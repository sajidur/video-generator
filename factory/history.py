"""History of every video made and every upload.

output/history.jsonl  one line per event (made / uploaded), never rewritten, only appended
output/history.csv    one row per video with its upload links (open it in Excel)
"""
import csv
import json
import subprocess
import time

from . import config

FILE = config.OUTPUT / "history.jsonl"
CSV = config.OUTPUT / "history.csv"
PLATFORMS = ("youtube", "facebook", "tiktok")


def add(event, **fields):
    _backfill()
    rec = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "event": event, **fields}
    FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load():
    _backfill()
    if not FILE.exists():
        return []
    out = []
    for line in FILE.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _backfill():
    """First run: import videos and uploads that were made before history existed."""
    if FILE.exists() or not config.OUTPUT.is_dir():
        return
    recs = []
    for d in sorted(p for p in config.OUTPUT.iterdir() if p.is_dir() and not p.name.startswith("_")):
        video = d / f"{d.name}.mp4"
        if not video.exists():
            continue
        title = ""
        sb = d / "storyboard.json"
        if sb.exists():
            try:
                title = json.loads(sb.read_text(encoding="utf-8")).get("title", "")
            except ValueError:
                pass
        try:
            seconds = round(float(subprocess.check_output(
                [config.find_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video)], text=True).strip()), 1)
        except (subprocess.CalledProcessError, ValueError, SystemExit):
            seconds = ""
        recs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(video.stat().st_mtime)),
                     "event": "made", "slug": d.name, "title": title, "file": str(video), "seconds": seconds,
                     "size_mb": round(video.stat().st_size / 1e6, 1), "note": "imported"})
        up = d / "uploads.json"
        if up.exists():
            try:
                for platform, info in json.loads(up.read_text(encoding="utf-8")).items():
                    recs.append({"time": info.get("time", ""), "event": "uploaded", "slug": d.name,
                                 "platform": platform, "url": info.get("url", ""), "note": "imported"})
            except ValueError:
                pass
    recs.sort(key=lambda r: r["time"])
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")


def videos():
    """One row per video: latest 'made' info + its upload links."""
    rows = {}
    for r in load():
        row = rows.setdefault(r.get("slug", "?"), {"slug": r.get("slug", "?")})
        if r["event"] == "made":
            row.update({k: r.get(k, "") for k in ("title", "style", "quality", "seconds", "size_mb", "file")})
            row["made"] = r["time"]
        elif r["event"] == "uploaded":
            row[r.get("platform", "?")] = r.get("url", "")
            row[f"{r.get('platform', '?')}_time"] = r["time"]
    return sorted(rows.values(), key=lambda x: x.get("made", ""))


def export_csv():
    cols = ["slug", "title", "made", "style", "quality", "seconds", "size_mb", *PLATFORMS, "file"]
    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel shows Bangla correctly
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(videos())
    return CSV


def show(log=print, limit=40):
    rows = videos()
    if not rows:
        log("No videos made yet.")
        return
    log(f"{'made':<17} {'video':<14} {'len':>5}  {'YouTube':<8} {'Facebook':<9} {'TikTok':<7} title")
    for r in rows[-limit:]:
        mark = {p: ("yes" if r.get(p) else "-") for p in PLATFORMS}
        secs = f"{float(r['seconds']):.0f}s" if r.get("seconds") else ""
        log(f"{r.get('made', '')[:16]:<17} {r['slug']:<14} {secs:>5}  {mark['youtube']:<8} "
            f"{mark['facebook']:<9} {mark['tiktok']:<7} {str(r.get('title', ''))[:60]}")
    up = {p: sum(1 for r in rows if r.get(p)) for p in PLATFORMS}
    log(f"\n{len(rows)} videos | uploaded: YouTube {up['youtube']}, Facebook {up['facebook']}, "
        f"TikTok {up['tiktok']} | full list with links: {export_csv()}")
