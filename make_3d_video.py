"""AI Video Factory - 3D edition.

Give it topics; it writes the script (local AI), voices it, builds animated 3D
scenes in Blender and exports a captioned vertical video per topic.

    python make_3d_video.py                       # every topic in topics.txt and topics/*.txt
    python make_3d_video.py "Why is the sky blue"  # one topic right now
    python make_3d_video.py --plan-only            # write storyboards only (edit, then run again)
    python make_3d_video.py --preview              # one still per shot -> preview.jpg (fast check)
    python make_3d_video.py --quality draft        # quick low-res test render
    python make_3d_video.py --list                 # numbered topics + which are done
    python make_3d_video.py --next                 # make just the next unfinished topic
    python make_3d_video.py --only 7               # make topic number 7 (or 5-10, or 1,4,9)

Run with --help for all options. Output: output/<topic>/<topic>.mp4
"""
import argparse
import re
import sys
import time

from factory import captions, compose, config, render, storyboard, voice
from factory.topics import Topic, detect_lang, load_topics


def parse_args():
    p = argparse.ArgumentParser(description="Turn topics into narrated 3D animated videos.")
    p.add_argument("topics", nargs="*", help="topic(s) to make now (default: topics.txt and topics/*.txt)")
    p.add_argument("--only", metavar="WHICH",
                   help="topic number(s) from --list (7, 5-10, 1,4,9) or text in the title / name")
    p.add_argument("--next", nargs="?", const=1, type=int, metavar="N",
                   help="make only the next N unfinished topics (default 1)")
    p.add_argument("--list", action="store_true", help="show the numbered topic list with status and stop")
    p.add_argument("--quality", choices=list(config.QUALITY), default="standard",
                   help="draft = fast 540p test, standard = 720p render upscaled to 1080p, high = native 1080p")
    p.add_argument("--lang", choices=["en", "bn"],
                   help="narration language (default: detected from the topic text; bn = Bangla)")
    p.add_argument("--voice", help="edge-tts voice, e.g. en-US-AndrewNeural (default depends on --lang)")
    p.add_argument("--rate", default="-5%", help="speaking speed, e.g. +10%%")
    p.add_argument("--model", default=config.DEFAULT_MODEL, help="Ollama model that writes the script")
    p.add_argument("--seconds", type=int, default=50, help="target video length when the AI writes the script")
    p.add_argument("--landscape", action="store_true", help="16:9 instead of 9:16")
    p.add_argument("--plan-only", action="store_true", help="write storyboard.json and stop")
    p.add_argument("--preview", action="store_true", help="render one still per shot into preview.jpg and stop")
    p.add_argument("--replan", action="store_true", help="throw away the saved storyboard and plan again")
    p.add_argument("--force", action="store_true", help="re-make videos that are already finished")
    p.add_argument("--no-ai", action="store_true", help="never use the AI model (needs your own narration)")
    p.add_argument("--no-titles", action="store_true", help="no floating 3D title words")
    p.add_argument("--music", help="background music file, or 'none' (default: a track from assets/music/)")
    return p.parse_args()


def log(msg=""):
    print(msg, flush=True)


def show_plan(board):
    name = f" ({board['hero_name']})" if board.get("hero_name") else ""
    log(f"  title: {board['title']}   hero: {board['hero']}{name}")
    for i, s in enumerate(board["shots"], 1):
        props = ", ".join(s["props"]) or "-"
        actor = "no actor" if s["character"] == "none" else \
            f"{s.get('hero', board['hero'])}/{s.get('outfit', 'casual')} {s['character']}"
        log(f"  {i:>2}. [{s['environment']}/{s['time']}] {actor} | {props} | {s['camera']}"
            f"{' | 3D: ' + s['title_3d'] if s.get('title_3d') else ''}")
        log(f"      \"{s['narration'][:90]}{'...' if len(s['narration']) > 90 else ''}\"")


def make(topic, args, q):
    out = config.OUTPUT / topic.slug
    out.mkdir(parents=True, exist_ok=True)
    final = out / f"{topic.slug}.mp4"
    sb_path = out / "storyboard.json"
    if (final.exists() and not (args.force or args.plan_only or args.preview or args.replan)
            and sb_path.exists() and sb_path.stat().st_mtime < final.stat().st_mtime):
        log(f"  already finished: {final}  (use --force to make it again)")
        return final

    # 1. storyboard (saved, so you can edit it and run again)
    if sb_path.exists() and not args.replan:
        log(f"  using saved storyboard: {sb_path}")
        raw = storyboard.load(sb_path)
        spoken = " ".join(str(s.get("narration", "")) for s in raw.get("shots", []))
        lang = args.lang or detect_lang(spoken)
        board = storyboard.sanitize(raw, raw.get("topic", topic.title), lang)
        if raw.get("lang") != lang:
            storyboard.save(board, sb_path)
    else:
        lang = args.lang or topic.lang
        board = storyboard.plan(topic, args.model, args.seconds, lang, use_llm=not args.no_ai, log=log)
        storyboard.save(board, sb_path)
        log(f"  storyboard saved: {sb_path}")
    show_plan(board)
    if args.plan_only:
        return None

    # 2. voice (one clip per shot, word-timed)
    v = args.voice or config.VOICES.get(lang, config.VOICES["en"])
    log(f"  language: {lang}   voice: {v}")
    if not v.lower().startswith(lang + "-"):
        log(f"  warning: voice {v} may not be able to speak '{lang}' text")
    clips = voice.synthesize(board, out / "audio", v, args.rate, log=log)
    tl = render.timeline(clips, q["fps"])
    log(f"  length: {tl['total_frames'] / q['fps']:.1f}s, {len(clips)} shots")
    job = render.make_job(board, topic.slug, tl, q, out, titles=not args.no_titles and lang == "en")

    if args.preview:
        render.run_blender(job, out, still=True, log=log)
        stills = [out / "frames" / f"preview_{i + 1:02d}.png" for i in range(len(job["shots"]))]
        compose.contact_sheet([p for p in stills if p.exists()], out / "preview.jpg")
        log(f"  preview: {out / 'preview.jpg'}")
        return None

    # 3. narration track + captions
    narration = out / "narration.wav"
    voice.build_track(clips, narration)
    caps = out / "captions.ass"
    w, h = q["out"]
    captions.write_ass(clips, [s["narration"] for s in board["shots"]], caps, w, h,
                       config.CAPTION_FONTS.get(lang, "Arial"))

    # 4. 3D render (resumable) and 5. final video
    render.run_blender(job, out, log=log)
    music = compose.pick_music(topic.slug, args.music)
    if music:
        log(f"  music: {music.name}")
    log("  encoding video ...")
    compose.compose(job, tl, narration, caps, final, q, music)
    return final


def status(topic):
    out = config.OUTPUT / topic.slug
    if (out / f"{topic.slug}.mp4").exists():
        return "done"
    if (out / "storyboard.json").exists():
        return "planned"
    return ""


def select(topics, which):
    """'7', '5-10', '1,4,9' pick by list number; anything else matches title or name."""
    which = which.strip()
    if re.fullmatch(r"[\d,\s-]+", which):
        picked = set()
        for part in which.split(","):
            a, _, b = part.strip().partition("-")
            if a.strip().isdigit():
                lo = int(a)
                hi = int(b) if b.strip().isdigit() else lo
                picked.update(range(lo, hi + 1))
        return [t for i, t in enumerate(topics, 1) if i in picked]
    w = which.lower()
    return [t for t in topics if w in t.title.lower() or w in t.slug]


def show_list(topics):
    marks = {"done": "[done]   ", "planned": "[planned]", "": "         "}
    for i, t in enumerate(topics, 1):
        log(f"{i:>4}. {marks[status(t)]} {t.slug:<14} {t.title}")
    done = sum(1 for t in topics if status(t) == "done")
    log(f"\n{done}/{len(topics)} done.  Next: python make_3d_video.py --next   "
        f"(or --only <number>)")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    q = dict(config.quality(args.quality, args.landscape), name=args.quality)
    todo = [Topic(t, source="command line") for t in args.topics] or load_topics()
    if args.list:
        show_list(todo)
        return 0
    if args.only:
        todo = select(todo, args.only)
    if args.next:
        todo = [t for t in todo if status(t) != "done"][:args.next]
    if not todo:
        log("No topics. Add one per line to topics.txt (or pass one: python make_3d_video.py \"My topic\").")
        return 1
    log(f"AI VIDEO FACTORY 3D: {len(todo)} topic(s), quality={args.quality} "
        f"({q['width']}x{q['height']} @ {q['fps']}fps -> {q['out'][0]}x{q['out'][1]})")
    done, failed = [], []
    for i, topic in enumerate(todo, 1):
        log(f"\n[{i}/{len(todo)}] {topic.title}  ({topic.source})")
        start = time.time()
        try:
            result = make(topic, args, q)
            if result:
                done.append(result)
                log(f"  DONE in {(time.time() - start) / 60:.1f} min -> {result}")
        except KeyboardInterrupt:
            log("\nStopped. Run the same command again to continue where it left off.")
            return 130
        except Exception as exc:  # keep going with the other topics
            failed.append(topic.title)
            log(f"  FAILED: {exc}")
    log(f"\nFinished: {len(done)} video(s){', failed: ' + '; '.join(failed) if failed else ''}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
