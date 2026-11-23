"""Paths, quality presets and tool discovery."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:  # API keys and settings live in .env (never committed)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OUTPUT = ROOT / "output"
TOPICS_FILE = ROOT / "topics.txt"
TOPICS_DIR = ROOT / "topics"
MUSIC_DIR = ROOT / "assets" / "music"
FOOTAGE_DIR = Path(os.environ.get("FOOTAGE_DIR") or ROOT / "assets" / "footage")  # your own clips
CREDENTIALS = ROOT / "credentials"  # OAuth tokens for uploading (never committed)
BLENDER_SCRIPTS = ROOT / "blender"


def env(name, default=""):
    return (os.environ.get(name) or default).strip()

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL


def ram_gb():
    """Installed memory in GB (0 if unknown)."""
    try:
        if os.name == "nt":
            import ctypes

            class _Mem(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = _Mem()
            m.dwLength = ctypes.sizeof(m)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 2 ** 30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except (OSError, ValueError, AttributeError):
        return 0.0


# script-writing models, best first: (name, download GB, memory needed GB)
MODELS = [("gemma4:12b", 8, 14), ("gemma3:4b", 3.3, 6)]


def recommended_model():
    ram = ram_gb() or 8
    return next((m for m, _, need in MODELS if ram >= need), MODELS[-1][0])


DEFAULT_MODEL = os.environ.get("FACTORY_MODEL") or recommended_model()
MODEL_CHOSEN = bool(os.environ.get("FACTORY_MODEL"))  # False: picked automatically

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


# real-footage videos need no 3D rendering, so they are always made at full size
FOOTAGE_QUALITY = {
    "draft": dict(width=720, height=1280, fps=30, out=(720, 1280)),
    "standard": dict(width=1080, height=1920, fps=30, out=(1080, 1920)),
    "high": dict(width=1080, height=1920, fps=30, out=(1080, 1920)),
}


def quality(name, landscape=False, style="3d"):
    q = dict((FOOTAGE_QUALITY if style == "footage" else QUALITY)[name])
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
