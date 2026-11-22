"""Paths, quality presets and tool discovery."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
TOPICS_FILE = ROOT / "topics.txt"
TOPICS_DIR = ROOT / "topics"
MUSIC_DIR = ROOT / "assets" / "music"
BLENDER_SCRIPTS = ROOT / "blender"

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL
DEFAULT_MODEL = os.environ.get("FACTORY_MODEL", "gemma3:4b")

# render size, fps and EEVEE samples; "out" is the final video size (upscaled by ffmpeg)
QUALITY = {
    "draft": dict(width=540, height=960, fps=12, samples=8, out=(540, 960)),
    "standard": dict(width=720, height=1280, fps=24, samples=16, out=(1080, 1920)),
    "high": dict(width=1080, height=1920, fps=30, samples=32, out=(1080, 1920)),
}

VOICES = {"en": "en-US-GuyNeural", "bn": "bn-BD-PradeepNeural"}
CAPTION_FONTS = {"en": "Arial Black", "bn": "Nirmala UI"}
TITLE_FONTS = ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
               "/System/Library/Fonts/Supplemental/Arial Black.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

ACCENTS = ["#ffd166", "#4cc9f0", "#f72585", "#06d6a0", "#ff9f1c", "#b8c0ff", "#ff6b6b", "#80ffdb"]


def quality(name, landscape=False):
    q = dict(QUALITY[name])
    if landscape:
        q["width"], q["height"] = q["height"], q["width"]
        q["out"] = (q["out"][1], q["out"][0])
    return q


def title_font():
    return next((f for f in TITLE_FONTS if Path(f).exists()), None)


def find_blender():
    candidates = [os.environ.get("BLENDER_PATH"), ROOT / "tools" / "blender" / "blender.exe",
                  ROOT / "tools" / "blender" / "blender", shutil.which("blender")]
    for base in (Path("C:/Program Files/Blender Foundation"), Path("/Applications/Blender.app/Contents/MacOS")):
        if base.exists():
            candidates += sorted(base.glob("*/blender.exe"), reverse=True) + [base / "Blender"]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise SystemExit(
        "Blender not found. Put a portable Blender in tools/blender/ (see README.md) "
        "or set BLENDER_PATH to blender.exe.")


def find_tool(name):
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} not found on PATH. Install FFmpeg (winget install Gyan.FFmpeg).")
    return path
