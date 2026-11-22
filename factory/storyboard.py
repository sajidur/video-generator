"""Topic -> storyboard (narration split into shots, each with a 3D scene plan).

Uses a local Ollama model with a JSON schema so the model can only pick
scene elements that exist. Without a model, your own narration is planned
with keyword matching instead.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import requests

from . import casting, config, vocab

LANG_NAMES = {"en": "English", "bn": "Bengali (Bangla script)"}
CAMERA_CYCLE = ["push_in", "orbit", "low_angle", "pan", "crane_up", "pull_out"]


# ------------------------------------------------------------------ ollama ---


def _tags():
    r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
    r.raise_for_status()
    return r.json()


def _start_ollama(log):
    """Start the local Ollama server in the background (like opening the Ollama app)."""
    exe = shutil.which("ollama") or next(
        (str(p) for p in [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"]
         if p.exists()), None)
    local = "localhost" in config.OLLAMA_URL or "127.0.0.1" in config.OLLAMA_URL
    if not exe or not local:
        return False
    log("  Ollama is not running - starting it ...")
    flags = 0x00000008 | 0x08000000 if sys.platform == "win32" else 0  # DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, creationflags=flags, start_new_session=sys.platform != "win32")
    for _ in range(30):
        time.sleep(1)
        try:
            _tags()
            return True
        except requests.RequestException:
            pass
    return False


def ollama_status(model, log=print):
    try:
        data = _tags()
    except requests.RequestException:
        if not _start_ollama(log):
            return False, f"Ollama is not running at {config.OLLAMA_URL} (open the Ollama app)."
        data = _tags()
    names = {m["name"] for m in data.get("models", [])}
    if model in names or f"{model}:latest" in names:
        return True, ""
    return False, f"Ollama model '{model}' is not installed. Run:  ollama pull {model}"


def _chat(model, system, user, schema, temperature=0.7):
    r = requests.post(f"{config.OLLAMA_URL}/api/chat", timeout=1800, json={
        "model": model, "stream": False, "format": schema,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": temperature, "num_ctx": 8192, "num_predict": 3500},
    })
    r.raise_for_status()
    text = r.json()["message"]["content"]
    try:
        return json.loads(text)
    except ValueError:
        return _salvage(text)


def _salvage(text):
    """Small models sometimes loop inside one sentence until they run out of room.
    Keep every shot that was finished before that happened."""
    end = text.rfind("}")
    while end > 0:
        try:
            data = json.loads(text[:end + 1] + "]}")
            if len(data.get("shots", [])) >= 4:
                return data
            break
        except ValueError:
            end = text.rfind("}", 0, end)
    raise ValueError("the AI reply was cut off (it got stuck repeating itself)")


def _enum(values):
    return {"type": "string", "enum": list(values)}


def _visual_props():
    return {
        "environment": _enum(vocab.ENVIRONMENTS),
        "time": _enum(vocab.TIMES),
        "props": {"type": "array", "items": _enum(vocab.PROPS), "maxItems": 3},
        "character": _enum(vocab.ACTIONS),
        "outfit": _enum(vocab.OUTFITS),
        "camera": _enum(vocab.CAMERAS),
        "title_3d": {"type": "string", "maxLength": 30},
    }


def _schema(with_narration):
    # maxLength keeps a looping model from writing one endless sentence
    shot = {"narration": {"type": "string", "maxLength": 320}} if with_narration else {}
    shot.update(_visual_props())
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 120},
            "hero": _enum(vocab.HEROES),
            "hero_name": {"type": "string", "maxLength": 40},
            "shots": {"type": "array", "minItems": 4, "maxItems": 12,
                      "items": {"type": "object", "properties": shot, "required": list(shot)}},
        },
        "required": ["title", "hero", "hero_name", "shots"],
    }


def _library_text():
    out = ["SCENE LIBRARY (use these exact names only)", "", "environment:"]
    out += [f"  {k}: {v}" for k, v in vocab.ENVIRONMENTS.items()]
    out += ["", "time: " + ", ".join(vocab.TIMES), "", "character (what the main character does):"]
    out += [f"  {k}: {v}" for k, v in vocab.ACTIONS.items()]
    out += ["", "camera:"] + [f"  {k}: {v}" for k, v in vocab.CAMERAS.items()]
    labels = {"icon": "floating symbols", "ground": "objects on the ground",
              "big": "huge background landmarks", "sky": "things in the sky"}
    for kind, label in labels.items():
        out += ["", f"props - {label}:"]
        out += [f"  {k}: {d}" for k, (kd, d) in vocab.PROPS.items() if kd == kind]
    out += ["", "outfit (what the main character wears in the shot):"]
    out += [f"  {k}: {v}" for k, v in vocab.OUTFITS.items()]
    out += ["", "hero (main character at the START of the story): " + ", ".join(vocab.HEROES)]
    return "\n".join(out)


SYSTEM = ("You write and direct short vertical 3D animated videos (YouTube Shorts, Reels, TikTok). "
          "You write gripping, simple narration and plan one 3D scene per shot using ONLY a fixed "
          "library of scene elements. Every visual choice must show what that shot's narration says.")

VISUAL_RULES = """Rules for each shot's visuals:
- environment: where the scene happens. Use at most 3 different environments in the whole video and
  keep consecutive shots in the same place while the story stays there.
- time: day, sunrise, sunset or night - match the mood.
- props: 2 or 3 items that SHOW what the narration says, most important first. Use "person" when the
  hero talks to one other person (customer, friend, parent) and "crowd" for many people.
- character: the main character's action must show the line's main verb: walk/run when going
  somewhere, carry when delivering or bringing something, talk when speaking or explaining, point when
  showing something, think when deciding or dreaming, work when working hard, read when learning, sad
  when struggling or failing, celebrate when succeeding, sit when resting or waiting.
  If the line is about the main character (their name, he, she), the character MUST appear - never
  "none". Use "none" only for lines about objects, places or facts.
- outfit: what the main character wears in this shot. It must fit their job and situation at that
  moment (poor when poor, shopkeeper while running a shop, suit when a successful businessman, ...).
- hero: gender and age of the main character at the start (the boy grows up on his own when years pass).
- hero_name: the main character's name if the story gives one, else "".
- camera: vary it between shots; fly_over or push_in make a good first shot.
- title_3d: 1 to 3 punchy ENGLISH words floating in 3D. Use it on the first shot and on at most
  two key moments; otherwise "".
"""


SCRIPT_RULES = {
    "bn": ("- লিখবেন শুধু বাংলায়, বাংলা অক্ষরে। কোনো ইংরেজি, হিন্দি বা গুজরাটি অক্ষর নয়।\n"
           "- Write ONLY in Bengali using Bengali script. Never switch to Hindi, Gujarati or English.\n"
           "- Use an everyday example from Bangladesh (a shop, a rickshaw, a tea stall, a mobile phone)."),
    "en": "- Write in simple spoken English.",
}


def _script_prompt(title, seconds, lang):
    words = int(seconds * 2.4)
    return f"""Topic: "{title}"

Write the voice-over script for a {seconds}-second vertical video (about {words} words in total).
Rules:
- Exactly 7 to 9 lines. Each line is one scene: 1 or 2 short spoken sentences (12 to 25 words).
- Line 1 is a hook: a surprising fact or a question. The last line is a memorable takeaway.
- If the topic names a book or author, mention it once, in the first or the last line.
- Explain the idea correctly and simply, with one everyday example.
{SCRIPT_RULES.get(lang, SCRIPT_RULES["en"])}
- Output ONLY the lines, one per line. No numbering, no title, no notes, no quotes, no stage directions.
"""


# Devanagari, Gurmukhi, Gujarati, ... but not Bengali, and not the danda "।" that Bangla shares
_OTHER_SCRIPTS = re.compile(r"[ऀ-ॣ०-ॿ਀-ൿ]")


def _clean_line(line):
    line = re.sub(r"^\s*(?:[-*•]|\(?[0-9০-৯]+[.)।:]?)\s*", "", line).strip()
    return line.strip(" \"'“”‘’`").strip()


def _line_ok(line, lang):
    if len(line.split()) < 3 or re.search(r"\b(words?|shots?|seconds?|fly_over|orbit|push_in)\b", line):
        return False
    if lang == "bn":
        bangla = sum(1 for ch in line if "ঀ" <= ch <= "৿")
        latin = sum(1 for ch in line if ch.isascii() and ch.isalpha())
        return bangla > 0 and not _OTHER_SCRIPTS.search(line) and latin <= 0.1 * bangla
    return line.isascii() or sum(ch.isascii() for ch in line) > 0.9 * len(line)


def _write_script(model, title, seconds, lang, log):
    """Step 1: plain-text narration (small models write far better without a JSON straitjacket)."""
    for attempt, temp in enumerate((0.7, 0.5, 0.8)):
        r = requests.post(f"{config.OLLAMA_URL}/api/chat", timeout=1800, json={
            "model": model, "stream": False,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": _script_prompt(title, seconds, lang)}],
            "options": {"temperature": temp, "num_ctx": 8192, "num_predict": 1500},
        })
        r.raise_for_status()
        raw = [_clean_line(x) for x in r.json()["message"]["content"].splitlines()]
        lines = [x for x in raw if x and _line_ok(x, lang)]
        dropped = len([x for x in raw if x]) - len(lines)
        if len(lines) >= 5:
            if dropped:
                log(f"  dropped {dropped} line(s) that were not clean {LANG_NAMES.get(lang, lang)}")
            return lines[:12]
        log(f"  script attempt {attempt + 1}: only {len(lines)} usable line(s); retrying ...")
    raise RuntimeError("the AI could not write a clean script for this topic; try --model gemma3:12b")


def _visuals_prompt(title, lines):
    numbered = "\n".join(f"{i + 1}. {ln}" for i, ln in enumerate(lines))
    return f"""Topic: "{title}"

The narration is already written. Plan exactly {len(lines)} shots, one per line, in order.
Copy each line into "narration" unchanged.

{numbered}

{VISUAL_RULES}
{_library_text()}
"""


# ---------------------------------------------------------------- fallback ---

_WORD = re.compile(r"[a-z]+")
_BN_WORD = re.compile(r"[ঀ-৿]+")


def _bn_words(text):
    text = unicodedata.normalize("NFC", text.replace("‌", "").replace("‍", ""))
    return _BN_WORD.findall(text)


def _bn_stems(s):
    return [unicodedata.normalize("NFC", x) for x in s.split()]


def _bn_hit(word, stems):
    return any(word.startswith(s) for s in stems)


def _keyword_best(text, group, limit=1):
    """Rank vocabulary names by keyword hits (English words and Bangla word stems)."""
    words = _WORD.findall(text.lower())
    bn = _bn_words(text)
    scores = {}
    for name, kws in vocab.KEYWORDS[group].items():
        kw = set(kws.split())
        stems = _bn_stems(vocab.KEYWORDS_BN[group].get(name, ""))
        # plural -> singular only for things ("coins" -> "coin"); never for verbs ("runs a company")
        hits = sum(1 for w in words if w in kw or (group != "actions" and len(w) > 4 and w[:-1] in kw
                                                       and w.endswith("s")))
        hits += sum(1 for w in bn if _bn_hit(w, stems))
        if hits:
            scores[name] = hits
    return [n for n, _ in sorted(scores.items(), key=lambda kv: -kv[1])][:limit]


PEOPLE = set("he she they i you we his her him their boy girl man woman child people person "
             "student farmer friend mother father family everyone someone".split())


def _mentions(text, english, bangla_key):
    words = set(_WORD.findall(text.lower()))
    stems = _bn_stems(vocab.KEYWORDS_BN[bangla_key])
    return bool(words & english) or any(_bn_hit(w, stems) for w in _bn_words(text))


def keyword_visuals(text, index, prev_env=None):
    envs = _keyword_best(text, "environments")
    props = _keyword_best(text, "props", 3)
    acted = _keyword_best(text, "actions")
    action = acted[0] if acted else "idle"
    if props and not acted and not _mentions(text, PEOPLE, "people"):
        action = "none"  # a line only about things: no character
    if _mentions(text, {"night", "dark", "sleep", "moon", "stars"}, "night"):
        time = "night"
    elif _mentions(text, {"sunset", "evening", "end", "finally"}, "sunset"):
        time = "sunset"
    elif _mentions(text, {"morning", "sunrise", "dawn", "begin", "began", "start"}, "sunrise"):
        time = "sunrise"
    else:
        time = "day"
    return {
        "environment": envs[0] if envs else (prev_env or "studio"),
        "time": time,
        "props": props,
        "character": action,
        "camera": "fly_over" if index == 0 else CAMERA_CYCLE[index % len(CAMERA_CYCLE)],
        "title_3d": "",
    }


def split_narration(text, min_words=7, max_words=20):
    """About one shot per sentence; very short sentences are glued to their neighbour."""
    text = " ".join(text.split())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]
    units, buf = [], ""
    for s in sentences:
        buf = f"{buf} {s}".strip()
        if len(buf.split()) >= 6:
            units.append(buf)
            buf = ""
    if buf:
        if units:
            units[-1] += " " + buf
        else:
            units.append(buf)
    shots, cur = [], []
    for s in units:
        n = len(" ".join(cur).split())
        if cur and (n >= min_words or n + len(s.split()) > max_words):
            shots.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        shots.append(" ".join(cur))
    return shots


# --------------------------------------------------------------- cleaning ---


def _clean_title3d(text, lang):
    if lang != "en":  # Blender can't draw non-Latin text, so 3D titles are English-only
        return ""
    text = re.sub(r"[^A-Za-z0-9 '!?&$%-]", "", str(text or "")).strip()
    words = text.split()
    return " ".join(words[:3]) if words and len(" ".join(words[:3])) <= 22 else ""


def sanitize(board, title, lang):
    shots = []
    prev_env = None
    for i, raw in enumerate(board.get("shots", [])):
        narration = " ".join(str(raw.get("narration", "")).split())
        if not narration:
            continue
        guess = keyword_visuals(narration, len(shots), prev_env)
        env = raw.get("environment") if raw.get("environment") in vocab.ENVIRONMENTS else guess["environment"]
        props = []
        for p in raw.get("props") or []:
            if p in vocab.PROPS and p not in props:
                props.append(p)
        if not props and raw.get("character") in (None, "none"):
            props = guess["props"]
        character = raw.get("character") if raw.get("character") in vocab.ACTIONS else guess["character"]
        shot = {
            "narration": narration,
            "environment": env,
            "time": raw.get("time") if raw.get("time") in vocab.TIMES else guess["time"],
            "props": props[:3],
            "character": character,
            "camera": raw.get("camera") if raw.get("camera") in vocab.CAMERAS else guess["camera"],
            "title_3d": _clean_title3d(raw.get("title_3d"), lang),
        }
        if re.fullmatch(r"#[0-9a-fA-F]{6}", str(raw.get("accent", ""))):
            shot["accent"] = raw["accent"]
        if raw.get("hero") in vocab.HEROES:  # the actor's form in this shot (set by casting)
            shot["hero"] = raw["hero"]
        if raw.get("outfit") in vocab.OUTFITS:
            shot["outfit"] = raw["outfit"]
        shots.append(shot)
        prev_env = env
    if not shots:
        raise ValueError("storyboard has no usable shots")
    out_title = " ".join(str(board.get("title") or title).split()) or title
    if lang == "bn" and not any("ঀ" <= ch <= "৿" for ch in out_title):
        out_title = title  # keep a Bangla title for a Bangla video
    if not shots[0]["title_3d"] and lang == "en":
        shots[0]["title_3d"] = _clean_title3d(out_title, lang)
    hero = board.get("hero") if board.get("hero") in vocab.HEROES else "boy"
    out = {"topic": title, "title": out_title, "lang": lang, "hero": hero,
           "hero_name": " ".join(str(board.get("hero_name") or "").split())[:40], "shots": shots[:12]}
    if board.get("outfit") in vocab.OUTFITS:
        out["outfit"] = board["outfit"]
    if isinstance(board.get("hero_look"), dict):
        out["hero_look"] = board["hero_look"]
    return out


LANDMARK_HOME = {"volcano": "mountains", "mountain": "mountains", "pyramid": "desert", "boat": "ocean"}
CRAMPED = {"city", "room", "studio"}  # landmarks get hidden by walls / skyscrapers here


def enrich(board):
    """Repair thin or odd AI plans (only right after planning, never on your edits)."""
    for shot in board["shots"]:
        home = next((LANDMARK_HOME[p] for p in shot["props"] if p in LANDMARK_HOME), None)
        if home and shot["environment"] in CRAMPED:
            shot["environment"] = home
        want = 2 if shot["props"] else (1 if shot["character"] != "none" else 2)
        for p in _keyword_best(shot["narration"], "props", 3):
            if len(shot["props"]) >= want:
                break
            if p not in shot["props"]:
                shot["props"].append(p)
    return board


# ------------------------------------------------------------------- main ---


def plan(topic, model, seconds=50, lang="en", use_llm=True, log=print):
    llm_ok, why = ollama_status(model, log) if use_llm else (False, "AI planning disabled (--no-ai)")
    written_by_ai = False
    if not topic.narration and llm_ok:
        log(f"  step 1/2: writing the script with {model} ...")
        lines = _write_script(model, topic.title, seconds, lang, log)
        written_by_ai = True
    if topic.narration or written_by_ai:
        lines = lines if written_by_ai else split_narration(topic.narration)
        if llm_ok:
            log(f"  {'step 2/2: ' if written_by_ai else ''}planning scenes for the narration with {model} ...")
            try:
                data = _chat(model, SYSTEM, _visuals_prompt(topic.title, lines), _schema(True), 0.5)
                planned = data.get("shots", [])
                shots = []
                for i, line in enumerate(lines):
                    v = planned[i] if i < len(planned) else keyword_visuals(line, i)
                    shots.append(dict(v, narration=line))
                return casting.cast(enrich(sanitize(dict(data, shots=shots), topic.title, lang)))
            except (requests.RequestException, ValueError, KeyError) as exc:
                log(f"  AI planning failed ({exc}); using keyword planning")
        else:
            log(f"  {why}\n  -> planning scenes from keywords instead")
        shots, prev = [], None
        for i, line in enumerate(lines):
            v = keyword_visuals(line, i, prev)
            prev = v["environment"]
            shots.append(dict(v, narration=line))
        return casting.cast(sanitize({"title": topic.title, "hero": "boy", "shots": shots}, topic.title, lang))

    raise RuntimeError(f"{why}\nEither start the AI model, or write the narration yourself in "
                       f"topics/<name>.txt (first line = title, then the narration).")


def seed_for(slug, index):
    return int(hashlib.sha1(f"{slug}:{index}".encode()).hexdigest()[:8], 16)


def save(board, path):
    path.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))
