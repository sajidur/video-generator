# AI Video Factory

You give it topics. For each one it:

1. writes a script and a shot-by-shot storyboard with a **local AI** (Ollama),
2. voices it with **edge-tts**, with word-level timing,
3. builds the pictures in one of two styles:
   - `--style footage`: **real video clips** from Pexels, Pixabay or your own `assets/footage/`
     folder, one per line and cut to fit. Ready in minutes.
   - `--style 3d`: **animated 3D scenes in Blender** with characters, props, camera moves and
     lighting. Takes about 40 min per video.
4. exports a captioned **vertical video** (9:16, 1080×1920) with cross-fades and optional music,
5. optionally **uploads** it to YouTube (Shorts), a Facebook Page (Reels) and TikTok.

**Footage and uploading need a one-time setup:** see [PUBLISHING.md](PUBLISHING.md).

```powershell
python make_3d_video.py --next --upload youtube,facebook,tiktok   # make the next topic and post it
```

Everything except the voice, the footage download and the uploads runs on this PC.

```
output/<topic>/<topic>.mp4     the video
output/<topic>/thumbnail.jpg   a thumbnail
output/<topic>/storyboard.json the plan (edit it and run again to change the video)
```

## Quick start

```powershell
venv\Scripts\activate
python make_3d_video.py --quality draft     # fast low-res test of every topic
python make_3d_video.py                     # full quality
```

## Giving it topics

**Just a topic (the AI writes the script):** add one line per topic to `topics.txt`. An optional
English name before ` | ` becomes the output folder name:

```
How volcanoes erupt
kotler-001 | মার্কেটিং আসলে কী? — ফিলিপ কটলারের ‘প্রিন্সিপলস অব মার্কেটিং’ বই থেকে
```

`topics.txt` currently holds **200 Bangla topics** from Philip Kotler's *Principles of Marketing*
(20 chapters × 10 topics, `kotler-001` … `kotler-200`). If a topic names a book, the AI mentions
the book in the narration.

**Your own narration:** create `topics/<anything>.txt`. The first line is the title and the rest is
the narration. The AI only plans the scenes and does not change your words. See
`topics/marketing.txt`.

### Making a long list one at a time

```powershell
python make_3d_video.py --list        # numbered list, shows which are [done] / [planned]
python make_3d_video.py --next        # make the next unfinished topic (--next 3 = the next three)
python make_3d_video.py --only 7      # make topic number 7   (also: --only 5-10, --only 1,4,9)
python make_3d_video.py --only kotler-042
```

**One-off from the command line:** `python make_3d_video.py "Why is the sky blue"`

Finished topics are skipped on later runs. Use `--force` to remake one.

### Bangla topics

Just write the topic or narration in Bangla, either as a line in `topics.txt` or as a
`topics/<name>.txt` file. The language is detected automatically:

- voice `bn-BD-PradeepNeural` (male). For a female voice use `--voice bn-BD-NabanitaNeural`.
- captions in Nirmala UI, with each spoken word highlighted
- the AI plans scenes for Bangla text, and without the AI, Bangla keywords pick the scenes
  (গ্রাম → village, দোকান → shop, টাকা → coins, স্বপ্ন → star …)
- floating 3D title words are switched off, because Blender cannot draw Bangla letters correctly
- name the file in English (e.g. `topics/marketing.txt`) and the output folder gets that name

If Ollama isn't running, the program starts it automatically.

## Recommended workflow

```powershell
python make_3d_video.py --plan-only   # 1. AI writes storyboard.json for each topic (~3 min each)
#   2. read/edit output/<topic>/storyboard.json if you like
python make_3d_video.py --preview     # 3. one still per shot -> output/<topic>/preview.jpg (~1 min)
python make_3d_video.py               # 4. full render
```

Rendering can be stopped at any time with Ctrl+C. Run the same command again and it continues
from the last finished frame. Shots you didn't change are never rendered twice.

## Options

| option | what it does |
|---|---|
| `--only volcano` | only the topics whose title contains that text |
| `--style footage` / `--style 3d` | real stock footage or Blender 3D animation |
| `--upload youtube,facebook,tiktok` | post each finished video (see PUBLISHING.md) |
| `--login youtube` | connect an account once (youtube, facebook or tiktok) |
| `--upload-existing --upload youtube` | upload videos that are already finished (never re-makes them) |
| `--no-upload` | skip uploading this run, even with `AUTO_UPLOAD` set in `.env` |
| `--quality draft / standard / high` | draft: 540p at 12 fps, fast test. standard: 720p render upscaled to 1080p at 24 fps (default). high: native 1080p at 30 fps. |
| `--lang bn` / `--lang en` | force the language. Normally it is detected from the topic text: Bangla text gets a Bangla voice and Bangla captions automatically. |
| `--voice en-US-AndrewNeural` | any edge-tts voice (`edge-tts --list-voices`) |
| `--rate +10%` | speaking speed |
| `--seconds 60` | target length when the AI writes the script |
| `--landscape` | 16:9 instead of 9:16 |
| `--model llama3.2:3b` | another Ollama model (smaller = faster, bigger = better writing) |
| `--replan` | throw away the saved storyboard and plan again |
| `--no-ai` | never call the AI; plan scenes from keywords (needs your own narration) |
| `--no-titles` | no floating 3D title words |
| `--music file.mp3` / `--music none` | background music. By default a track is picked from `assets/music/` if that folder has any. |

### Render time on this laptop (Intel Iris Xe)

| quality | speed | 50-second video |
|---|---|---|
| `draft` (540×960, 12 fps) | ~1.4 s/frame | ~15 min |
| `standard` (720×1280 → 1080×1920, 24 fps) | ~2 s/frame | ~40 min |
| `high` (1080×1920, 30 fps) | ~4–5 s/frame | ~2 h |

The AI storyboard takes another 3–4 minutes per topic on the CPU. The very first render also spends a
minute or two compiling shaders. A good habit is to queue several topics and let them run overnight,
or while the laptop is plugged in. A laptop on battery renders much slower.

## The actor matches the story

After planning, a casting step goes through every shot so the main character fits the line:

- **Who:** gender and age come from the story (boy, girl, ছেলে, মেয়ে, old, বৃদ্ধ …). The face and
  colours stay the same all video, but the actor **grows up** when the story jumps ahead ("years
  passed", "বছর পর", "বড় হয়ে") or takes a grown-up job.
- **What they wear:** the outfit follows the story and stays until it changes. For example: poor
  clothes → shop apron when they open a shop → suit when they succeed. The outfits are casual, poor,
  suit, farmer (straw hat and lungi), shopkeeper, doctor, student and worker.
- **What they do:** whenever a line is about the hero (their name, he/she, সে/তার), the hero is in
  the shot, and the action follows the verb:

  | the line says | action |
  |---|---|
  | goes, walks / হাঁটে, গিয়ে | walk |
  | delivers, brings / পৌঁছে দিত | carry (with a parcel) |
  | says, explains / বলল, বোঝাল | talk (turns to the other person) |
  | shows / দেখাল | point (at the object) |
  | works hard / কাজ, পরিশ্রম | work (types at a laptop or phone, otherwise hammers) |
  | decides, dreams / সিদ্ধান্ত, স্বপ্ন | think |
  | learns / পড়া, শেখা | read |
  | sad, poor, failed / হতাশ, কষ্ট | sad |
  | succeeds / সফল, জনপ্রিয় | celebrate |
  | sits / বসে | sit (on a stool) |

  Lines addressed to the viewer ("Remember…", "মনে রাখবেন…") get the hero presenting them.
  `person` adds one other character (customer, friend, parent) who faces the hero and talks.

Everything the casting step decides is written into `storyboard.json` (`hero`, `outfit` and
`character` on each shot), so you can still change any of it by hand.

## Editing a storyboard

Each shot in `storyboard.json` looks like this:

```json
{
  "narration": "Deep inside the Earth, magma builds up tremendous pressure.",
  "environment": "mountains",
  "time": "sunset",
  "props": ["volcano", "earth"],
  "character": "think",
  "camera": "push_in",
  "title_3d": ""
}
```

Change any value, save, and run again. Only the changed shots are re-rendered, and the voice is only
regenerated for narration lines you changed. Allowed values:

- **environment:** village, forest, city, space, ocean, desert, mountains, snow, room, studio
- **time:** day, sunrise, sunset, night
- **character** (what the actor does): none, idle, walk, run, wave, celebrate, think, read, sad,
  talk, point, work, carry, sit
- **hero** (the actor's form in this shot): boy, girl, man, woman, old_man, old_woman, robot
- **outfit:** casual, poor, suit, farmer, shopkeeper, doctor, student, worker
- **camera:** orbit, push_in, pull_out, pan, crane_up, low_angle, fly_over
- **props** (up to 3):
  - icons: lightbulb, heart, star, dollar, lock, magnifier, atom, dna, virus, gear, clock, trophy, question, medical, speech_bubble, shield, lightning
  - on the ground: tree, pine_tree, house, car, rocket, books, coins, laptop, phone, bar_chart, campfire, flag, boat, wind_turbine, flowers, rocks, crowd, person, signpost, stairs, factory
  - landmarks: mountain, volcano, pyramid, buildings
  - sky: sun, moon, planet, earth, clouds, birds, airplane

Optional extras: `"accent": "#ff006e"` on a shot sets the title/accent colour. A top-level
`"hero_look": {"shirt": "#e63946", "skin": "#c68642", "hair": "#2b1d0e", "pants": "#1d3557"}` sets
the main character's colours.

## How it fits together

```
make_3d_video.py        command line / orchestration
factory/topics.py       reads topics.txt and topics/*.txt
factory/storyboard.py   Ollama prompt + JSON schema, keyword fallback, validation
factory/casting.py      makes the actor (age, outfit, action) match every line
factory/footage.py      real footage: own clips, Pexels, Pixabay; search, download, cut
factory/publish.py      upload to YouTube, Facebook Page, TikTok (+ one-time logins)
factory/voice.py        edge-tts per shot with word timings, padded narration track
factory/captions.py     word-highlighted ASS captions
factory/render.py       frame timeline, Blender job, resumable rendering
factory/compose.py      ffmpeg cross-fades, upscale, captions, music
factory/vocab.py        the scene vocabulary shared by the AI planner and Blender
blender/shot.py         Blender entry: layout, camera rig, 3D titles, render loop
blender/worlds.py       the 10 environments (sky, ground, lights, set dressing)
blender/props.py        49 procedural props
blender/character.py    rigged low-poly character, outfits and 14 actions
blender/kit.py          primitives, shared materials, stateless animation system
tools/blender/          portable Blender 4.5 LTS (used automatically)
```

**Adding a new prop:** describe it in `factory/vocab.py` (`PROPS`, and `KEYWORDS` if you like), then
write a function with the same name in `blender/props.py` that returns
`Built(root, height, width)`. Blender refuses to start if a prop in the vocabulary has no builder.

## Setup on a new machine (Windows)

```powershell
git clone https://github.com/sajidur/video-generator.git
cd video-generator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
winget install Gyan.FFmpeg          # ffmpeg + ffprobe on PATH
winget install Ollama.Ollama        # local AI that writes the scripts
ollama pull gemma3:4b
```

Blender is not in the repository because it's too big. Download the portable
**Blender 4.5 LTS** zip for Windows from <https://download.blender.org/release/Blender4.5/> and
unpack it so that `tools/blender/blender.exe` exists. Alternatively, set `BLENDER_PATH` to an
installed `blender.exe`.

Ollama is optional if you write every narration yourself. edge-tts (the voice) needs internet.
`output/` (rendered videos and frames) is not in git.

The old single-image pipeline (`generate_video.py`) is unchanged and still works.
