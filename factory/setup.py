"""Easy setup for new users.

  python make_video.py --setup    guided wizard: tools, keys, auto-upload, account logins
  python make_video.py --doctor   check everything and say how to fix what is missing
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

from . import config

ENV = config.ROOT / ".env"
EXAMPLE = config.ROOT / ".env.example"
CRED_FILES = {"youtube": "youtube_token.json", "facebook": "facebook.json", "tiktok": "tiktok.json"}


# ------------------------------------------------------------------ helpers ---


def _ok(log, good, label, fix=""):
    log(f"  [{'OK' if good else '!!'}] {label}" + ("" if good else f"\n         -> {fix}"))
    return good


def _ask(prompt, default=""):
    try:
        answer = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    except EOFError:
        answer = ""
    return answer or default


def _yes(prompt, default=True):
    answer = _ask(f"{prompt} ({'Y/n' if default else 'y/N'})").lower()
    return default if not answer else answer.startswith("y")


def _read_env():
    src = ENV if ENV.exists() else EXAMPLE
    values = {}
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                values[m.group(1)] = m.group(2).strip()
    return values


def _write_env(updates):
    """Change only the given keys; keep every other line (and comment) of .env as it is."""
    lines = (ENV if ENV.exists() else EXAMPLE).read_text(encoding="utf-8").splitlines() \
        if (ENV.exists() or EXAMPLE.exists()) else []
    seen = set()
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Z_]+)=", line.strip())
        if m and m.group(1) in updates:
            lines[i] = f"{m.group(1)}={updates[m.group(1)]}"
            seen.add(m.group(1))
    lines += [f"{k}={v}" for k, v in updates.items() if k not in seen]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    for k, v in updates.items():  # use the new values in this run too
        os.environ[k] = v


def _ollama_exe():
    path = shutil.which("ollama")
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return path or (str(local) if local.exists() else None)


def _winget(package, log):
    if not shutil.which("winget"):
        log(f"  winget is not available; install {package} by hand.")
        return
    subprocess.run(["winget", "install", "--id", package, "-e", "--accept-source-agreements",
                    "--accept-package-agreements"])


# ----------------------------------------------------------------- blender ---


def download_blender(log=print):
    """Portable Blender 4.5 LTS into tools/blender (checksum verified)."""
    if sys.platform != "win32":
        log("  Automatic download is for Windows; install Blender 4.5 from https://www.blender.org/download/")
        return False
    base = "https://download.blender.org/release/Blender4.5/"
    html = requests.get(base, timeout=30).text
    versions = sorted(set(re.findall(r"blender-(4\.5\.\d+)-windows-x64\.zip", html)),
                      key=lambda v: tuple(int(x) for x in v.split(".")))
    if not versions:
        log("  Could not find a Blender 4.5 download.")
        return False
    v = versions[-1]
    name = f"blender-{v}-windows-x64.zip"
    expected = next((ln.split()[0] for ln in requests.get(f"{base}blender-{v}.sha256", timeout=30).text.splitlines()
                     if ln.strip().endswith(name)), "")
    tmp_dir = config.ROOT / "tools" / "_download"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zpath = tmp_dir / name
    log(f"  downloading Blender {v} (~400 MB) ...")
    digest = hashlib.sha256()
    with requests.get(base + name, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done, shown = 0, -1
        with open(zpath, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                pct = int(done * 100 / total) if total else 0
                if pct // 10 != shown:
                    shown = pct // 10
                    log(f"    {pct}%")
    if expected and digest.hexdigest() != expected:
        zpath.unlink(missing_ok=True)
        log("  Download was damaged (checksum mismatch). Run setup again.")
        return False
    log("  unpacking ...")
    with zipfile.ZipFile(zpath) as z:
        z.extractall(config.ROOT / "tools")
    target = config.ROOT / "tools" / "blender"
    if target.exists():
        shutil.rmtree(target)
    (config.ROOT / "tools" / name[:-4]).rename(target)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    log(f"  Blender {v} is ready.")
    return True


# ------------------------------------------------------------------ doctor ---


def doctor(log=print):
    from . import footage, publish
    from .storyboard import ollama_status
    from .topics import load_topics
    log("Checking your setup ...\n")
    ok = True
    for mod, pkg in (("edge_tts", "edge-tts"), ("PIL", "pillow"), ("dotenv", "python-dotenv"),
                     ("googleapiclient", "google-api-python-client"), ("google_auth_oauthlib", "google-auth-oauthlib")):
        try:
            __import__(mod)
            good = True
        except ImportError:
            good = False
        ok &= _ok(log, good, f"Python package {pkg}", "run setup.bat again (or: pip install -r requirements.txt)")
    for tool in ("ffmpeg", "ffprobe"):
        ok &= _ok(log, bool(shutil.which(tool)), tool, "winget install Gyan.FFmpeg   (then open a new window)")

    has_footage = footage.available()
    style = config.env("VIDEO_STYLE") or ("footage" if has_footage else "3d")
    if style == "footage" and not has_footage:
        style = "3d"
    _ok(log, has_footage, "footage source for real-video style (Pexels / Pixabay key or assets/footage)",
        "free key: https://www.pexels.com/api/  -> run setup again or put PEXELS_API_KEY=... in .env")
    try:
        config.find_blender()
        has_blender = True
    except SystemExit:
        has_blender = False
    blender_ok = _ok(log, has_blender, "Blender (for 3D style)", "run setup again and let it download Blender")
    if style == "3d":
        ok &= blender_ok
    log(f"  -> videos will be made in style: {style}")

    good, why = ollama_status(config.DEFAULT_MODEL, log=lambda m: None)
    _ok(log, good, f"AI writer: Ollama model {config.DEFAULT_MODEL}",
        why or "install Ollama (https://ollama.com) and run: ollama pull " + config.DEFAULT_MODEL)
    try:
        requests.head("https://speech.platform.bing.com", timeout=6)
        online = True
    except requests.RequestException:
        online = False
    ok &= _ok(log, online, "internet (needed for the voice)", "check your connection")

    auto = [p.strip() for p in config.env("AUTO_UPLOAD").split(",") if p.strip()]
    for p in publish.PLATFORMS:
        connected = (config.CREDENTIALS / CRED_FILES[p]).exists()
        label = f"{p} account" + (" (auto-upload is on)" if p in auto else "")
        if p == "youtube" and connected:
            try:
                channel = publish.youtube_channel()
                label += f": channel '{channel}'" if channel else ""
                if not channel:
                    ok &= _ok(log, False, label, "this Google account has no YouTube channel: create one at "
                              "https://www.youtube.com/create_channel (or log in with the account that owns your "
                              "channel), then: python make_video.py --login youtube")
                    continue
            except Exception as exc:
                text = str(exc)
                if "insufficientPermissions" in text or "insufficient authentication scopes" in text:
                    why = "connected with an older login that cannot show the channel - reconnect once"
                elif "youtubeSignupRequired" in text:
                    why = "this Google account has no YouTube channel - create one, then reconnect"
                else:
                    why = f"login problem ({text[:100]})"
                ok &= _ok(log, False, label, f"{why}:  python make_video.py --login youtube")
                continue
        if p in auto:
            ok &= _ok(log, connected, label, f"python make_video.py --login {p}   (see PUBLISHING.md)")
        else:
            log(f"  [{'OK' if connected else '--'}] {label}{'' if connected else ' not connected (optional)'}")
    n = len(load_topics())
    ok &= _ok(log, n > 0, f"{n} topics in topics.txt / topics/", "add one topic per line to topics.txt")
    log("\nAll good - ready to make videos." if ok else "\nFix the [!!] items above, then run the check again.")
    return ok


# ------------------------------------------------------------------ wizard ---


def wizard(log=print):
    from . import publish
    log("=" * 60)
    log(" AI Video Factory - setup")
    log(" Press Enter to accept the value in [brackets].")
    log("=" * 60)
    if not ENV.exists() and EXAMPLE.exists():
        shutil.copy(EXAMPLE, ENV)
    env = _read_env()
    upd = {}

    log("\n1) Tools")
    if not shutil.which("ffmpeg"):
        if _yes("FFmpeg (video tool) is missing. Install it now?"):
            _winget("Gyan.FFmpeg", log)
            log("  Close this window and run setup again afterwards, so FFmpeg is found.")
    else:
        log("  FFmpeg: ok")
    if not _ollama_exe():
        if _yes("Install Ollama (the local AI that writes the scripts)?"):
            _winget("Ollama.Ollama", log)
    exe = _ollama_exe()
    if exe:
        from .storyboard import ollama_status
        good, _ = ollama_status(config.DEFAULT_MODEL, log=lambda m: None)
        if good:
            log(f"  AI model {config.DEFAULT_MODEL}: ok")
        elif _yes(f"Download the AI model {config.DEFAULT_MODEL} (about 3 GB)?"):
            subprocess.run([exe, "pull", config.DEFAULT_MODEL])

    log("\n2) Video style")
    log("  footage = real video clips (needs a free Pexels or Pixabay key)")
    log("  3d      = animated 3D scenes made in Blender (slower, no key needed)")
    style = _ask("Style", env.get("VIDEO_STYLE") or "footage").lower()
    upd["VIDEO_STYLE"] = "3d" if style.startswith("3") else "footage"
    for key, url in (("PEXELS_API_KEY", "https://www.pexels.com/api/"),
                     ("PIXABAY_API_KEY", "https://pixabay.com/api/docs/")):
        current = env.get(key, "")
        val = _ask(f"{key} (free at {url}){' - already set, Enter keeps it' if current else ' - Enter to skip'}")
        if val:
            upd[key] = val
    needs_3d = upd["VIDEO_STYLE"] == "3d" or not (upd.get("PEXELS_API_KEY") or env.get("PEXELS_API_KEY")
                                                    or upd.get("PIXABAY_API_KEY") or env.get("PIXABAY_API_KEY"))
    try:
        config.find_blender()
        log("  Blender: ok")
    except SystemExit:
        if needs_3d and _yes("3D videos need Blender. Download it now (about 400 MB)?"):
            download_blender(log)

    log("\n3) Uploading")
    log("  Which platforms should every new video be posted to automatically?")
    auto = _ask("youtube, facebook, tiktok - comma separated, or 'none'", env.get("AUTO_UPLOAD") or "none")
    platforms = [p.strip().lower() for p in auto.split(",") if p.strip().lower() in publish.PLATFORMS]
    upd["AUTO_UPLOAD"] = ",".join(platforms)
    if "facebook" in platforms:
        for key in ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"):
            if not env.get(key):
                upd[key] = _ask(f"{key} (developers.facebook.com -> your app -> Settings -> Basic)")
    if "tiktok" in platforms:
        for key in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"):
            if not env.get(key):
                upd[key] = _ask(f"{key} (developers.tiktok.com -> your app)")
    if "youtube" in platforms and not (config.CREDENTIALS / "youtube_client_secret.json").exists():
        config.CREDENTIALS.mkdir(exist_ok=True)
        log(f"  YouTube: save your Google OAuth client file as {config.CREDENTIALS / 'youtube_client_secret.json'}")
        log("  (PUBLISHING.md section 2 shows how to get it)")
        _ask("Press Enter when the file is there (or to skip)")
    _write_env({k: v for k, v in upd.items() if v is not None})
    log("  settings saved to .env")

    for p in platforms:
        if (config.CREDENTIALS / CRED_FILES[p]).exists():
            log(f"  {p}: already connected")
            continue
        if _yes(f"Connect your {p} account now?"):
            try:
                publish.login(p, log)
            except Exception as exc:
                log(f"  {p} login failed: {exc}\n  You can retry later: python make_video.py --login {p}")

    log("")
    doctor(log)
    log("\nNext: double-click start.bat (or run: python make_video.py --next)")
