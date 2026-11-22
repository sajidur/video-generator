
import asyncio
import edge_tts

TEXT = """
Hello everyone! Welcome to our story.
Today we will discover how a little boy
changed his life through hard work and determination.
"""

VOICE = "en-US-GuyNeural"

async def generate_voice():
    communicate = edge_tts.Communicate(
        TEXT,
        VOICE,
        rate="+0%",
        pitch="+0%"
    )

    await communicate.save("story_voice.mp3")
    print("Voice generated: story_voice.mp3")

asyncio.run(generate_voice())