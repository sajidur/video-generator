"""Timeline maths + running Blender to render every shot's frames."""
import collections
import hashlib
import json
import random
import subprocess
import time
from pathlib import Path

from . import casting, config, vocab, voice
from .storyboard import seed_for

CROSSFADE = 0.5  # seconds


def timeline(clips, fps):
    """Frame plan so cross-fades are centred on the narration boundaries.

    Returns per-shot frame counts, head overlaps (frames) and the overlap length X.
    The joined video (sum(frames) - (n-1)*X) matches the narration track exactly.
    """
    bounds, total = [0], 0.0
    for c in clips:
        total += c["segment"]
        bounds.append(round(total * fps))
    x = 2 * max(1, round(CROSSFADE * fps / 2))
    n = len(clips)
    frames, heads = [], []
    for i in range(n):
        head = x // 2 if i > 0 else 0
        tail = x // 2 if i < n - 1 else 0
        frames.append(bounds[i + 1] - bounds[i] + head + tail)
        heads.append(head)
    return {"fps": fps, "frames": frames, "heads": heads, "overlap": x, "total_frames": bounds[-1]}


def _code_hash():
    h = hashlib.sha1()
    for p in sorted(config.BLENDER_SCRIPTS.glob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()[:8]


def _seed(text):
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16)


def make_cast(board, slug):
    """The other people in the video. Each keeps one face and outfit in every shot.

    board["cast"] (from the AI or your edits): [{"name": "করিম", "type": "man", "outfit": "casual"}, ...].
    Without one, the video gets one consistent partner (customer / friend)."""
    hero = board.get("hero", "man")
    cast = []
    for m in board.get("cast") or []:
        if not isinstance(m, dict):
            continue
        kind = m.get("type") if m.get("type") in vocab.HEROES and m.get("type") != "robot" else "man"
        cast.append({"name": str(m.get("name", ""))[:40], "type": kind, "seed": _seed(f"{slug}:cast:{m.get('name')}"),
                     "outfit": m.get("outfit") if m.get("outfit") in vocab.OUTFITS else "casual",
                     "look": m.get("look") if isinstance(m.get("look"), dict) else {}})
    if not cast:
        kinds = [k for k in ("woman", "man", "old_man", "old_woman") if k != hero]
        cast.append({"name": "", "type": random.Random(slug + ":partner").choice(kinds),
                     "seed": _seed(f"{slug}:partner"), "outfit": "casual"})
    return cast[:3]


def make_job(board, slug, tl, q, outdir, titles=True, clips=None):
    code = _code_hash()
    hero = {"type": board.get("hero", "boy"), "seed": random.Random(slug).randrange(1 << 30)}
    hero.update(board.get("hero_look") or {})
    cast = make_cast(board, slug)
    names = [m["name"] for m in cast]
    shots = []
    for i, shot in enumerate(board["shots"]):
        env_seed = _seed(f"{slug}:place:{shot['environment']}")  # the same place looks the same in every shot
        spec = {
            "index": i, "frames": tl["frames"][i], "head": round(tl["heads"][i] / tl["fps"], 4),
            "seed": seed_for(slug, i), "environment": shot["environment"], "time": shot["time"],
            "props": shot["props"], "character": shot["character"], "camera": shot["camera"],
            "hero": shot.get("hero") or board.get("hero", "boy"), "outfit": shot.get("outfit", "casual"),
            "title_3d": shot.get("title_3d", "") if titles else "",
            "accent": shot.get("accent") or config.ACCENTS[(seed_for(slug, 99) + i) % len(config.ACCENTS)],
            "env_seed": env_seed, "env_accent": config.ACCENTS[env_seed % len(config.ACCENTS)],
            "partner": names.index(shot["with"]) if shot.get("with") in names else 0,
            "speaker": casting.speaker(board, shot),
        }
        if spec["speaker"] and clips:
            start = spec["head"] + voice.LEAD
            spec["mouth"] = voice.mouth_levels(clips[i]["audio"], tl["fps"], spec["frames"], start,
                                               ffmpeg=config.find_tool("ffmpeg"))
        key = json.dumps([spec, hero, cast, q["width"], q["height"], q["fps"], q["samples"], code], sort_keys=True)
        spec["out_dir"] = str(outdir / "frames" / f"shot_{i + 1:02d}_{hashlib.sha1(key.encode()).hexdigest()[:8]}")
        shots.append(spec)
    return {"fps": q["fps"], "width": q["width"], "height": q["height"], "samples": q["samples"],
            "quality": q["name"], "titles": titles, "font_bold": config.title_font(), "hero": hero,
            "cast": cast, "shots": shots}


def _cleanup_stale(outdir, job):
    from shutil import rmtree
    keep = {spec["out_dir"] for spec in job["shots"]}
    frames = outdir / "frames"
    if frames.is_dir():
        for d in frames.iterdir():
            if d.is_dir() and str(d) not in keep:
                rmtree(d, ignore_errors=True)


def run_blender(job, outdir, still=False, log=print):
    job_path = outdir / ("preview_job.json" if still else "render_job.json")
    job_path.write_text(json.dumps(job, indent=1), encoding="utf-8")
    if not still:
        _cleanup_stale(outdir, job)
        todo = [s for s in job["shots"] if not (Path(s["out_dir"]) / "done.json").exists()]
        if not todo:
            log("  all shots already rendered")
            return
        frames = sum(s["frames"] for s in todo)
        log(f"  rendering {len(todo)} shot(s), {frames} frames at {job['width']}x{job['height']} "
            f"(first run compiles shaders; safe to stop with Ctrl+C and resume later)")
    cmd = [config.find_blender(), "-b", "--factory-startup", "-noaudio", "--python-exit-code", "1",
           "-P", str(config.BLENDER_SCRIPTS / "shot.py"), "--", str(job_path)] + (["--still"] if still else [])
    tail = collections.deque(maxlen=40)
    start = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", cwd=str(config.ROOT))
    try:
        for line in proc.stdout:
            line = line.rstrip()
            tail.append(line)
            if line.startswith("[shot]"):
                log("  " + line[7:])
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        raise
    if proc.returncode != 0:
        raise RuntimeError("Blender failed:\n" + "\n".join(tail))
    log(f"  blender finished in {(time.time() - start) / 60:.1f} min")
