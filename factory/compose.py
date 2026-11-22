"""ffmpeg: rendered frames + narration + captions (+ music) -> final MP4."""
import subprocess
from pathlib import Path

from . import config


def _filter_path(path):
    """Path usable inside an ffmpeg filter argument (relative to ROOT when possible)."""
    path = Path(path).resolve()
    try:
        return path.relative_to(config.ROOT).as_posix()
    except ValueError:
        return path.as_posix().replace(":", "\\:")


def pick_music(slug, choice=None):
    if choice == "none":
        return None
    if choice:
        return Path(choice)
    if not config.MUSIC_DIR.is_dir():
        return None
    tracks = sorted(p for p in config.MUSIC_DIR.iterdir() if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg"))
    return tracks[sum(map(ord, slug)) % len(tracks)] if tracks else None


def compose(job, tl, narration, captions, out_mp4, q, music=None, music_volume=0.12):
    ffmpeg = config.find_tool("ffmpeg")
    fps, x = tl["fps"], tl["overlap"]
    shots = job["shots"]
    n = len(shots)
    cmd = [ffmpeg, "-y", "-v", "error", "-stats"]
    for s in shots:
        cmd += ["-framerate", str(fps), "-i", str(Path(s["out_dir"]) / "%04d.png")]
    cmd += ["-i", str(narration)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    parts = [f"[{i}:v]setsar=1,format=yuv420p[v{i}]" for i in range(n)]
    last, offset = "v0", 0
    for i in range(1, n):
        offset += tl["frames"][i - 1] - x
        parts.append(f"[{last}][v{i}]xfade=transition=fade:duration={x / fps:.4f}:offset={offset / fps:.4f}[x{i}]")
        last = f"x{i}"
    w, h = q["out"]
    post = []
    if (w, h) != (q["width"], q["height"]):
        post.append(f"scale={w}:{h}:flags=lanczos")
    post.append("vignette=angle=0.5")
    post.append(f"subtitles=filename='{_filter_path(captions)}'")
    parts.append(f"[{last}]{','.join(post)}[vout]")
    total = tl["total_frames"] / fps
    if music:
        parts.append(f"[{n + 1}:a]aresample=48000,volume={music_volume}[m]")
        parts.append(f"[{n}:a][m]amix=inputs=2:duration=first:normalize=0,"
                     f"afade=t=out:st={max(0.0, total - 1.5):.3f}:d=1.5[aout]")
    else:
        parts.append(f"[{n}:a]anull[aout]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
            "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(out_mp4)]
    subprocess.run(cmd, check=True, cwd=str(config.ROOT))
    thumb = out_mp4.with_name("thumbnail.jpg")
    subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", f"{min(1.5, total / 2):.2f}", "-i", str(out_mp4),
                    "-frames:v", "1", "-update", "1", "-q:v", "2", str(thumb)], check=True)


def contact_sheet(images, out_jpg, cell_w=300):
    """Grid of preview stills (one per shot) for checking a storyboard quickly."""
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in images]
    if not ims:
        return
    cell_h = int(cell_w * ims[0].height / ims[0].width)
    cols = min(5, len(ims))
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cell_w + 8) + 8, rows * (cell_h + 8) + 8), "white")
    for i, im in enumerate(ims):
        tile = im.resize((cell_w, cell_h))
        ImageDraw.Draw(tile).text((8, 8), f"shot {i + 1}", fill="white")
        sheet.paste(tile, (8 + (i % cols) * (cell_w + 8), 8 + (i // cols) * (cell_h + 8)))
    sheet.save(out_jpg, quality=90)
