"""Word-timed captions (ASS) with the spoken word highlighted, Shorts style."""
import re

from .voice import LEAD

WHITE = "&H00FFFFFF"
HIGHLIGHT = "&H0000E5FF"  # yellow (ASS colours are &HAABBGGRR)


def _ts(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _norm(w):
    return re.sub(r"[\W_]+", "", w.lower())


def _with_punctuation(words, narration):
    """edge-tts word timings drop punctuation; take the display text from the narration."""
    tokens = narration.split()
    out, j = [], 0
    for w in words:
        text = w["text"]
        for k in range(j, min(j + 3, len(tokens))):
            if _norm(tokens[k]) and _norm(tokens[k]) == _norm(text):
                text, j = tokens[k], k + 1
                break
        out.append(dict(w, text=text))
    return out


def _chunks(words, max_words=4, max_chars=22):
    chunk = []
    for w in words:
        if chunk and (len(chunk) >= max_words or len(" ".join(x["text"] for x in chunk + [w])) > max_chars):
            yield chunk
            chunk = []
        chunk.append(w)
        if w["text"] and w["text"][-1] in ".!?,;:।":
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _esc(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def write_ass(clips, narrations, path, width, height, font):
    size = int(height * 0.043)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{WHITE},{WHITE},&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,{max(3, size // 12)},{max(2, size // 25)},2,{int(width * 0.08)},{int(width * 0.08)},{int(height * 0.2)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    offset = 0.0
    for clip, narration in zip(clips, narrations):
        words = _with_punctuation(clip["words"], narration)
        base = offset + LEAD
        chunks = list(_chunks(words))
        for ci, chunk in enumerate(chunks):
            c_end = chunk[-1]["end"]
            if ci + 1 < len(chunks):
                c_end = max(c_end, min(chunks[ci + 1][0]["start"], c_end + 0.4))
            else:
                c_end += 0.3
            for wi, w in enumerate(chunk):
                start = w["start"] if wi else chunk[0]["start"]
                end = chunk[wi + 1]["start"] if wi + 1 < len(chunk) else c_end
                parts = [("{\\c" + HIGHLIGHT + "&}" + _esc(x["text"]) + "{\\c" + WHITE + "&}") if k == wi
                         else _esc(x["text"]) for k, x in enumerate(chunk)]
                pop = "{\\fscx108\\fscy108\\t(0,90,\\fscx100\\fscy100)}" if wi == 0 else ""
                events.append(f"Dialogue: 0,{_ts(base + start)},{_ts(base + end)},Cap,,0,0,0,,{pop}{' '.join(parts)}")
        offset += clip["segment"]
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
