"""Real video footage for every shot.

Sources, in order:
  1. your own clips in assets/footage/ (matched by file name: "shopkeeper-grocery-store.mp4")
  2. Pexels videos    (free, licensed for commercial use, needs PEXELS_API_KEY in .env)
  3. Pixabay videos   (free, licensed for commercial use, needs PIXABAY_API_KEY in .env)

Downloads and search results are cached in output/_footage, so re-runs cost nothing.
"""
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import requests

from . import config

CACHE = config.OUTPUT / "_footage"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


def available():
    """True when at least one footage source is configured."""
    return bool(config.env("PEXELS_API_KEY") or config.env("PIXABAY_API_KEY") or _local_files())


def probe(path):
    out = subprocess.check_output([
        config.find_tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)], text=True)
    data = json.loads(out)
    st = (data.get("streams") or [{}])[0]
    return float(data["format"]["duration"]), int(st.get("width", 0)), int(st.get("height", 0))


# ----------------------------------------------------------------- sources ---


def _local_files():
    if not config.FOOTAGE_DIR.is_dir():
        return []
    return [p for p in config.FOOTAGE_DIR.rglob("*") if p.suffix.lower() in VIDEO_EXT]


def _words(text):
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) > 2}


def search_local(query):
    want = _words(query)
    found = []
    for p in _local_files():
        score = len(want & _words(p.stem))
        if score:
            try:
                dur, w, h = probe(p)
            except (subprocess.CalledProcessError, KeyError, ValueError):
                continue
            found.append({"id": "local-" + hashlib.sha1(str(p).encode()).hexdigest()[:10], "path": str(p),
                          "width": w, "height": h, "duration": dur, "credit": "", "page": "",
                          "bonus": 10 * score})
    return found


def _cached_search(provider, query, orientation, fetch):
    key = hashlib.sha1(f"{provider}|{query}|{orientation}".encode()).hexdigest()[:16]
    path = CACHE / "search" / f"{provider}-{key}.json"
    if path.exists() and time.time() - path.stat().st_mtime < 14 * 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    results = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results), encoding="utf-8")
    return results


def search_pexels(query, orientation):
    api_key = config.env("PEXELS_API_KEY")
    if not api_key:
        return []

    def fetch():
        r = requests.get("https://api.pexels.com/videos/search", timeout=30, headers={"Authorization": api_key},
                         params={"query": query, "orientation": orientation, "per_page": 20, "size": "medium"})
        r.raise_for_status()
        out = []
        for v in r.json().get("videos", []):
            files = [f for f in v.get("video_files", [])
                     if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
            if not files:
                continue
            # the smallest file that is still at least ~HD on its short side (avoid huge 4K downloads)
            files.sort(key=lambda f: min(f["width"], f["height"]))
            good = [f for f in files if min(f["width"], f["height"]) >= 1000] or files[::-1]
            f = good[0]
            out.append({"id": f"pexels-{v['id']}", "url": f["link"], "width": f["width"], "height": f["height"],
                        "duration": float(v.get("duration") or 0),
                        "credit": f"{(v.get('user') or {}).get('name', 'Pexels')} / Pexels", "page": v.get("url", "")})
        return out
    return _cached_search("pexels", query, orientation, fetch)


def search_pixabay(query, orientation):
    api_key = config.env("PIXABAY_API_KEY")
    if not api_key:
        return []

    def fetch():
        r = requests.get("https://pixabay.com/api/videos/", timeout=30,
                         params={"key": api_key, "q": query[:100], "per_page": 30, "safesearch": "true"})
        r.raise_for_status()
        out = []
        for h in r.json().get("hits", []):
            vids = h.get("videos") or {}
            f = next((vids[k] for k in ("large", "medium", "small") if (vids.get(k) or {}).get("url")), None)
            if not f or not f.get("width"):
                continue
            out.append({"id": f"pixabay-{h['id']}", "url": f["url"], "width": f["width"], "height": f["height"],
                        "duration": float(h.get("duration") or 0),
                        "credit": f"{h.get('user', 'Pixabay')} / Pixabay", "page": h.get("pageURL", "")})
        return out
    return _cached_search("pixabay", query, orientation, fetch)


# ---------------------------------------------------------------- choosing ---


def _score(c, need, portrait):
    s = c.get("bonus", 0)
    is_portrait = c["height"] > c["width"]
    s += 6 if is_portrait == portrait else 0
    s += 4 if c["duration"] >= need + 0.5 else -3 * max(0.0, need - c["duration"])
    s += min(c["width"], c["height"]) / 1080
    return s


def _broader(query):
    words = query.split()
    out = [query]
    while len(words) > 1:
        words = words[:-1]
        out.append(" ".join(words))
    return out


def _download(c, log):
    if c.get("path"):
        return Path(c["path"])
    dest = CACHE / "clips" / f"{c['id']}.mp4"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    log(f"    downloading {c['id']} ({c['width']}x{c['height']}, {c['duration']:.0f}s)")
    with requests.get(c["url"], stream=True, timeout=120, headers={"User-Agent": "video-factory/1.0"}) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)
    return dest


def find_clip(query, need, used, portrait=True, fallbacks=(), log=print):
    """Best unused clip for `query` lasting `need` seconds. Tries broader queries, then fallbacks."""
    orientation = "portrait" if portrait else "landscape"
    tried = []
    for q in [*_broader(query), *fallbacks]:
        if not q or q in tried:
            continue
        tried.append(q)
        cands = search_local(q)
        for search in (search_pexels, search_pixabay):
            try:
                cands += search(q, orientation)
            except requests.RequestException as exc:
                log(f"    {search.__name__[7:]} search failed for '{q}': {exc}")
        cands = [c for c in cands if c["id"] not in used]
        if not cands:
            continue
        best = max(cands, key=lambda c: _score(c, need, portrait))
        try:
            path = _download(best, log)
        except requests.RequestException as exc:
            log(f"    download failed ({exc}); trying another clip")
            used.add(best["id"])
            continue
        used.add(best["id"])
        return dict(best, path=str(path), query=q)
    return None


# --------------------------------------------------------- whole storyboard ---


def build_shots(board, tl, q, out, log=print):
    """Find, download and cut one clip per shot. Returns (job for compose, credits)."""
    from . import storyboard, vocab
    fps, width, height = tl["fps"], q["width"], q["height"]
    portrait = height > width
    clipdir = out / "clips"
    clipdir.mkdir(parents=True, exist_ok=True)
    plans = []
    for i, s in enumerate(board["shots"]):
        seconds = tl["frames"][i] / fps
        query = s.get("footage") or storyboard.footage_query(s, board.get("lang", "en"))
        key = hashlib.sha1(f"{query}|{seconds:.3f}|{width}x{height}|{fps}".encode()).hexdigest()[:8]
        dest = clipdir / f"shot_{i + 1:02d}_{key}.mp4"
        plans.append((i, s, seconds, query, dest, dest.with_suffix(".json")))
    used = {json.loads(meta.read_text(encoding="utf-8"))["id"]
            for *_, dest, meta in plans if dest.exists() and meta.exists()}
    shots, credits = [], []
    for i, s, seconds, query, dest, meta in plans:
        if dest.exists() and meta.exists():
            info = json.loads(meta.read_text(encoding="utf-8"))
        else:
            fallbacks = [storyboard.footage_query(dict(s, props=[]), "en"),
                         vocab.FOOTAGE_HINTS["environment"].get(s.get("environment"), ""), "people city life"]
            c = find_clip(query, seconds, used, portrait, fallbacks, log)
            if not c:
                raise RuntimeError(f"no footage found for shot {i + 1} ('{query}'). Add a PEXELS_API_KEY / "
                                   f"PIXABAY_API_KEY to .env, or put a clip named after it in assets/footage/")
            cut(c["path"], dest, seconds, width, height, fps, seed=i * 37)
            info = {k: c.get(k, "") for k in ("id", "credit", "page", "query")}
            meta.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
        log(f"  shot {i + 1}/{len(plans)}: '{query}' -> {info['id']}"
            f"{' (searched: ' + info['query'] + ')' if info.get('query') not in ('', query) else ''}")
        shots.append({"index": i, "clip": str(dest)})
        credits.append(info)
    keep = {p[4].name for p in plans} | {p[5].name for p in plans}
    for old in clipdir.iterdir():
        if old.name not in keep:
            old.unlink(missing_ok=True)
    return {"shots": shots}, credits


def still(clip, out_png):
    """One frame from the middle of a clip (for --preview contact sheets)."""
    dur, _, _ = probe(clip)
    subprocess.run([config.find_tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{dur / 2:.2f}", "-i", str(clip),
                    "-frames:v", "1", "-update", "1", str(out_png)], check=True)


# ----------------------------------------------------------------- cutting ---


def cut(src, out, seconds, width, height, fps, seed=0):
    """Cut `seconds` of footage, cropped to fill width x height. Short clips are slowed slightly / looped."""
    dur, _, _ = probe(src)
    slow = 1.0
    if dur < seconds:
        slow = min(seconds / max(dur, 0.1), 1.35)
    usable = dur * slow
    loop = usable < seconds
    spare = max(0.0, usable - seconds)
    start = 0.0 if loop else min(spare, 0.4 + (seed % 100) / 100 * spare * 0.6) / slow
    vf = (f"setpts={slow:.4f}*PTS," if slow > 1.0 else "") + \
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}," \
        f"fps={fps},eq=contrast=1.04:saturation=1.08,format=yuv420p,setsar=1"
    cmd = [config.find_tool("ffmpeg"), "-y", "-v", "error"]
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-ss", f"{start:.3f}", "-i", str(src), "-t", f"{seconds:.4f}", "-vf", vf, "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", str(out)]
    subprocess.run(cmd, check=True)
