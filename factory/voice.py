"""Narration: one edge-tts clip per shot (with word timings), then one padded track."""
import array
import asyncio
import hashlib
import json
import math
import subprocess
import time

import edge_tts

LEAD = 0.2   # silence before each shot's line
TAIL = 0.35  # silence after it
END_TAIL = 1.2
# The voice service adds ~1 s of silence after every clip. Speech really ends ~0.12 s after the
# last word's timestamp, so each clip is cut this long after it (keeps scenes from dragging).
SPEECH_PAD = 0.25


async def _tts(text, voice, rate, mp3):
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    tmp = mp3.with_suffix(".part")
    with open(tmp, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append({"start": start, "end": start + chunk["duration"] / 1e7, "text": chunk["text"]})
    tmp.replace(mp3)
    return words


def duration(path, ffprobe="ffprobe"):
    out = subprocess.check_output([ffprobe, "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True)
    return float(out.strip())


def _even_words(text, dur):
    toks = text.split()
    step = dur / max(1, len(toks))
    return [{"start": i * step, "end": (i + 1) * step, "text": t} for i, t in enumerate(toks)]


def synthesize(board, folder, voice, rate="+0%", log=print):
    """Returns one dict per shot: audio path, speech length, segment length, word timings."""
    folder.mkdir(parents=True, exist_ok=True)
    clips = []
    n = len(board["shots"])
    for i, shot in enumerate(board["shots"]):
        text = shot["narration"]
        key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:10]
        mp3 = folder / f"shot_{i + 1:02d}_{key}.mp3"
        meta = mp3.with_suffix(".json")
        if not (mp3.exists() and meta.exists()):
            time.sleep(1.0)  # back-to-back requests make the free service drop some
            tries = 6
            for attempt in range(tries):
                try:
                    words = asyncio.run(_tts(text, voice, rate, mp3))
                    break
                except Exception as exc:  # the free voice service sometimes hiccups: retry
                    if attempt == tries - 1:
                        hint = "check your internet connection and try again"
                        if isinstance(exc, edge_tts.exceptions.NoAudioReceived):
                            bangla = any("ঀ" <= ch <= "৿" for ch in text)
                            if bangla != voice.lower().startswith("bn-"):
                                hint = ("the voice does not match the narration language "
                                        "(Bangla needs a bn-BD voice, English an en- voice)")
                            else:
                                hint = "the voice service returned nothing; wait a minute and run again"
                        raise RuntimeError(f"voice '{voice}' failed on shot {i + 1}: {exc} -> {hint}") from exc
                    wait = 3 + 4 * attempt
                    log(f"  voice service hiccup on shot {i + 1} ({exc}); retrying in {wait}s ...")
                    time.sleep(wait)
            speech = duration(mp3)
            if not words:
                words = _even_words(text, speech)
            meta.write_text(json.dumps({"speech": speech, "words": words}, ensure_ascii=False), encoding="utf-8")
        data = json.loads(meta.read_text(encoding="utf-8"))
        speech = data["speech"]
        if data["words"]:
            speech = min(speech, data["words"][-1]["end"] + SPEECH_PAD)
        seg = LEAD + speech + (END_TAIL if i == n - 1 else TAIL)
        clips.append({"audio": mp3, "speech": speech, "segment": seg, "words": data["words"]})
    for old in folder.glob("shot_*.*"):  # drop clips of narration lines that were edited away
        if not any(old.stem == c["audio"].stem for c in clips):
            old.unlink(missing_ok=True)
    return clips


def mouth_levels(audio, fps, frames, start, ffmpeg="ffmpeg"):
    """How open a speaker's mouth is on each frame of a shot (0..1), from the voice's loudness.

    start: shot time (seconds) at which this clip's audio begins."""
    sr = 16000
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(audio), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = array.array("h")
    pcm.frombytes(raw[: len(raw) // 2 * 2])
    hop = sr / fps
    rms = []
    for f in range(frames):
        i0 = int((f / fps - start) * sr)
        seg = pcm[max(0, i0):max(0, min(len(pcm), int(i0 + hop)))]
        rms.append(math.sqrt(sum(x * x for x in seg) / len(seg)) if len(seg) else 0.0)
    loud = sorted(v for v in rms if v > 0)
    peak = loud[int(len(loud) * 0.95)] if loud else 1.0
    out, prev = [], 0.0
    for v in rms:
        v = min(1.0, max(0.0, (v / peak - 0.12) / 0.88))
        prev = 0.65 * v + 0.35 * prev  # a little smoothing so the mouth doesn't flicker
        out.append(round(prev, 2))
    return out


def build_track(clips, out_wav, ffmpeg="ffmpeg"):
    """Concatenate clips, each padded to its exact segment length."""
    cmd = [ffmpeg, "-y", "-v", "error"]
    for c in clips:
        cmd += ["-i", str(c["audio"])]
    parts = []
    for i, c in enumerate(clips):
        parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,atrim=0:{c['speech']:.4f},"
                     f"adelay={int(LEAD * 1000)}:all=1,apad,atrim=0:{c['segment']:.4f}[a{i}]")
    concat = "".join(f"[a{i}]" for i in range(len(clips)))
    graph = ";".join(parts) + f";{concat}concat=n={len(clips)}:v=0:a=1[out]"
    cmd += ["-filter_complex", graph, "-map", "[out]", "-c:a", "pcm_s16le", str(out_wav)]
    subprocess.run(cmd, check=True)
