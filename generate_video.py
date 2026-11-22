
import asyncio
import subprocess
import textwrap
from pathlib import Path
import edge_tts
print("AI VIDEO FACTORY STARTED")
BASE = Path(__file__).parent
IMAGE = BASE / "assets" / "images" / "image01.png"
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)

AUDIO = OUTPUT / "narration.mp3"
SUBTITLE = OUTPUT / "subtitles.srt"
VIDEO = OUTPUT / "story_video.mp4"

# Change this story whenever you want
STORY = """
Once upon a time, there lived a poor boy
in a small village.

He had a big dream, but nobody believed in him.

Every morning, he woke up early,
worked hard and continued learning.

Years passed. His determination changed his life.

Remember, your background does not define
your future. Your hard work does.
"""

VOICE = "en-US-GuyNeural"

def run(command):
    subprocess.run(command, check=True, cwd=BASE)

async def generate_voice():
    communicate = edge_tts.Communicate(
        STORY,
        VOICE,
        rate="-5%",
        pitch="+0Hz"
    )
    await communicate.save(str(AUDIO))
    print("Voice generated!")

def get_audio_duration():
    result = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(AUDIO)
    ], text=True)

    return float(result.strip())

def timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}".replace(".", ",")

def generate_subtitles(duration):
    words = STORY.split()
    chunks = [
        " ".join(words[i:i+8])
        for i in range(0, len(words), 8)
    ]

    total_words = sum(len(c.split()) for c in chunks)
    current = 0
    entries = []

    for index, chunk in enumerate(chunks, 1):
        start = current
        end = current + duration * len(chunk.split()) / total_words
        current = end

        entries.append(
            f"{index}\n"
            f"{timestamp(start)} --> {timestamp(end)}\n"
            f"{textwrap.fill(chunk, width=32)}\n"
        )

    SUBTITLE.write_text("\n".join(entries), encoding="utf-8")
    print("Subtitles generated!")

def generate_video(duration):
    frames = int(duration * 30)

    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan=z='min(zoom+0.0005,1.08)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s=1080x1920:fps=30,"
        "subtitles=output/subtitles.srt:"
        "force_style='FontName=Arial,FontSize=22,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=3,Shadow=1,MarginV=130'"
    )

    run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", str(IMAGE),
        "-i", str(AUDIO),
        "-vf", video_filter,
        "-frames:v", str(frames),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(VIDEO)
    ])

    print("Video created:", VIDEO)

def main():
    if not IMAGE.exists():
        raise FileNotFoundError(
            f"Please add your image: {IMAGE}"
        )

    asyncio.run(generate_voice())

    duration = get_audio_duration()
    generate_subtitles(duration)
    generate_video(duration)

if __name__ == "__main__":
    main()
