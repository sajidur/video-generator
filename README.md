# AI Video Factory

Turn a list of topics into finished, narrated short videos and post them to YouTube, Facebook and
TikTok automatically. It works in **English and Bangla**.

For every topic it:

1. **Writes the script** with a free AI that runs on your own computer (Ollama), or uses your own
   narration.
2. **Plans every scene** so the pictures and the actor match each line of the script.
3. **Records the voice** (natural Microsoft voices, Bangla and English) with word-by-word timing.
4. **Makes the pictures** in one of two styles:
   - **footage:** real video clips (Pexels, Pixabay or your own clips), cut to each line. Ready in a
     few minutes.
   - **3d:** animated 3D scenes made in Blender, with a presenter or story character. No key
     needed.
5. **Edits the video:** vertical 1080×1920, captions where the spoken word lights up yellow, a
   title banner, crossfades, levelled sound, optional music.
6. **Posts it** to YouTube Shorts, Facebook Page Reels and TikTok, and keeps a **history** of
   everything.

---

## Install (Windows 10/11)

1. **Python 3.11 or newer:** <https://www.python.org/downloads/>. In the installer, tick
   **"Add python.exe to PATH"**.
2. **Get this folder:** download the ZIP from GitHub and unzip it, or
   `git clone https://github.com/sajidur/video-generator.git`.
3. **Double-click `setup.bat`** and answer the questions. It:
   - installs everything it needs: FFmpeg, the Ollama AI, the best AI model your computer can run
     (3–18 GB, see below) and, for 3D
     videos, Blender (~400 MB);
   - asks for your free footage key and where to post videos;
   - connects your YouTube / Facebook / TikTok accounts;
   - finishes with a check, so you know everything works.

You can run `setup.bat` again at any time to change settings.

> **Accounts for posting** need a one-time developer setup on each platform (free).
> [PUBLISHING.md](PUBLISHING.md) walks you through it step by step.

---

## Everyday use

**Double-click `start.bat`:**

```
  1. Make the next video  (posted automatically if auto-upload is on)
  2. Make a topic by number
  3. Show the topic list
  4. Preview a topic (one picture per scene, fast)
  5. Upload finished videos that are not posted yet
  6. History: every video and where it was posted
  7. Check setup
  8. Setup / change settings / connect accounts
```

The same commands in a terminal (inside the folder, after `venv\Scripts\activate`):

```powershell
python make_video.py --next              # make the next unfinished topic (and post it)
python make_video.py --only 17           # make topic 17  (also 17-20 or 1,4,9)
python make_video.py --list              # numbered topic list with [done] / [planned]
python make_video.py --history           # every video + where it was posted
python make_video.py --doctor            # check the setup
```

Stop at any time with **Ctrl+C**. Running the same command again continues where it stopped, and
nothing is made or posted twice.

---

## Your topics

**Let the AI write the script:** put one topic per line in `topics.txt`. An optional short English
name before ` | ` becomes the folder name:

```
How volcanoes erupt
kotler-001 | মার্কেটিং আসলে কী? — ফিলিপ কটলারের ‘প্রিন্সিপলস অব মার্কেটিং’ বই থেকে
```

**Write the narration yourself:** create `topics/<name>.txt`. The first line is the title and the
rest is your narration. The AI only plans the scenes; your words are kept exactly.

**Bangla** is detected automatically. You get a Bangla voice (`--voice bn-BD-NabanitaNeural` for a
female voice), Bangla captions and Bangla titles.

`topics.txt` comes with **200 Bangla marketing topics** based on Philip Kotler's *Principles of
Marketing* (20 chapters × 10 topics).

**Exact meaning.** The AI writes the script, then checks it again as a strict editor (facts,
the real textbook definition, every part of the idea, broken words) and corrects it. It can still be
wrong sometimes: for an educational channel, run `--plan-only` on a batch, read the `narration`
lines in `output/<topic>/storyboard.json`, fix anything wrong, then make the videos.

### Which AI model

The AI runs on your own computer (free). Setup picks the best one that fits your memory:

| model | memory | time per script | quality (tested on the Bangla Kotler topics) |
|---|---|---|---|
| `gemma4:26b` | 32 GB | ~4 min | best: exact definitions, all parts of the idea, natural Bangla |
| `gemma4:12b` | 16 GB | ~8 min | very good |
| `gemma3:4b` | 8 GB | ~1.5 min | often vague, incomplete or wrong — check every script |

To choose one yourself, put `FACTORY_MODEL=gemma4:12b` in `.env` (or use `--model` once), and
download it first with `ollama pull gemma4:12b`.

---

## What you get per video

```
output/<topic>/<topic>.mp4      the video
output/<topic>/thumbnail.jpg    a thumbnail
output/<topic>/storyboard.json  the plan: script, scenes, actor (edit it and run again)
output/<topic>/post.json        title, description, hashtags used for posting (editable)
output/<topic>/uploads.json     where it was posted, with links
output/history.csv              every video and its links, opens in Excel
```

---

## Settings (`.env`)

`setup.bat` writes this file for you. You can also edit it in Notepad.

| setting | meaning |
|---|---|
| `VIDEO_STYLE` | `footage` (real clips) or `3d`. Uses 3D automatically until a footage key is set. |
| `PEXELS_API_KEY`, `PIXABAY_API_KEY` | free footage keys: <https://www.pexels.com/api/>, <https://pixabay.com/api/docs/> |
| `AUTO_UPLOAD` | post every new video, e.g. `youtube,facebook`. Empty = never post automatically. |
| `YOUTUBE_PRIVACY` | `public`, `unlisted` or `private` |
| `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` | for posting to your Page (see PUBLISHING.md) |
| `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_MODE` | for TikTok (`direct` or `draft`) |

`.env` and the `credentials/` folder hold your private keys and logins. They are never uploaded to
GitHub, and you should never share them.

---

## All options

| option | what it does |
|---|---|
| `--next [N]` | make the next N unfinished topics (default 1) |
| `--only 7` / `5-10` / `1,4,9` / `kotler-042` | pick topics by number or name |
| `--list` | numbered topic list with status |
| `--history` | every video made and where it was posted (also writes `output/history.csv`) |
| `--style footage` / `--style 3d` | choose the picture style for this run |
| `--quality draft / standard / high` | draft = quick test; standard = full HD (default) |
| `--preview` | one still per scene → `output/<topic>/preview.jpg` (fast check) |
| `--plan-only` | only write the script + scene plan |
| `--replan` | throw away the saved plan and write a new one |
| `--force` | make a finished video again |
| `--upload youtube,facebook,tiktok` | post this run's videos (overrides `AUTO_UPLOAD`) |
| `--no-upload` | don't post this time |
| `--upload-existing` | post finished videos that aren't posted yet (never re-makes them) |
| `--login youtube` / `facebook` / `tiktok` | connect an account (one time) |
| `--setup` / `--doctor` | guided setup / check everything |
| `--lang bn` / `--lang en` | force the language (normally detected) |
| `--voice NAME`, `--rate +10%` | another edge-tts voice / speaking speed |
| `--seconds 60` | target length when the AI writes the script |
| `--landscape` | 16:9 instead of 9:16 |
| `--music file.mp3` / `--music none` | background music (default: a track from `assets/music/`, if any) |
| `--model gemma4:12b` | use another Ollama model for this run (see "Which AI model") |
| `--no-ai` | plan scenes from keywords only (needs your own narration) |

---

## Changing a video

Every scene in `output/<topic>/storyboard.json` looks like this:

```json
{
  "narration": "যেমন, পাড়ার চায়ের দোকান অফিসযাত্রীদের জন্য সকালে দ্রুত চা দেয় ...",
  "environment": "village", "time": "sunrise",
  "props": ["person", "house"],
  "character": "talk", "hero": "man", "outfit": "casual",
  "camera": "push_in",
  "footage": "tea stall street morning"
}
```

Change anything, save, and run the same topic again. Only the changed scenes are redone. Allowed
values:

- **environment:**
  - everyday and business places: shop, market (bazaar street), office, cafe (tea stall), classroom,
    warehouse, room, city, studio (abstract ideas)
  - nature: village, forest, mountains, desert, snow, ocean, space
- **time:** day, sunrise, sunset, night
- **character** (what the actor does): none, idle, walk, run, wave, celebrate, think, read, sad,
  talk, listen, point, work, carry, sit, give (sell / serve), buy (pay), shake_hands, phone, write,
  announce (megaphone), thumbs_up, clap, shrug, drink (tea), push_cart, search
- **hero:** boy, girl, man, woman, old_man, old_woman, robot
- **outfit:** casual, poor, suit, office, farmer, shopkeeper, chef, delivery, doctor, teacher, student,
  worker, police, traditional (panjabi / saree), sports
- **camera:** orbit, push_in, pull_out, pan, crane_up, low_angle, fly_over
- **footage:** English words to search real clips with (footage style)
- **props** (up to 3):
  - icons: lightbulb, heart, star, dollar, lock, magnifier, atom, dna, virus, gear, clock, trophy,
    question, medical, speech_bubble, shield, lightning, megaphone, target, price_tag, pie_chart, gift,
    magnet, rating, likes, balance
  - on the ground: tree, pine_tree, house, car, rocket, books, coins, laptop, phone, bar_chart,
    down_chart, campfire, flag, boat, wind_turbine, flowers, rocks, crowd, person, signpost, stairs,
    factory, shopping_bag, shopping_cart, boxes, truck, shopfront, billboard, whiteboard, tv, produce,
    rickshaw
  - landmarks: mountain, volcano, pyramid, buildings
  - sky: sun, moon, planet, earth, clouds, birds, airplane

### Every scene matches its line (3D style)

After the AI plans the scenes, two checks go over every line:

- **Place:** the scene happens where the line's example happens. A tea-stall example plays at the tea
  stall, a mobile seller in a shop, a company in an office. A village, forest or mountain top is only
  used when the story is really about it.
- **Props:** things the line names come first: "advertising" shows a megaphone, "price" a price tag,
  "segments" a pie chart, "social media" like bubbles.
- **Who:** age and gender come from the story. The actor grows up when the story jumps ahead
  ("years passed", "বছর পর").
- **Clothes:** the outfit follows the story, for example poor clothes, then a shop apron, then a suit.
- **Action:** follows the verb. Selling means handing over a product, paying means holding out money,
  a deal means a handshake, delivering means carrying a parcel, learning means reading.
- **The other person reacts:** when the actor sells, the customer pays; when the actor talks, they
  listen and nod; a crowd claps for an announcement.
- **Explainers:** topics that talk to "you" get one consistent presenter (everyday clothes, suit,
  office wear or teacher).

### Real speaking and a real cast

- **Lip-sync:** in explainers the presenter says the narration: the mouth opens and closes with the
  loudness of the voice, frame by frame, and the camera comes a little closer. In stories a narrator
  tells the story; a character speaks only lines written as dialogue ("..."). People who talk in the
  background move their mouths too.
- **Same people all video:** the other person (customer, friend) keeps one face and outfit in every
  scene. Named people in a story (for example Rakib's customer Karim) each get their own fixed look.
- **Many looks:** hijab, beard, moustache, tupi, glasses, different hair (bun, ponytail, curly,
  spiky), slim / heavy builds, heights, skin and clothes colours.
- **Busy places:** shoppers and a cashier in the shop, family at home, people on the street, villagers,
  tea drinkers, office colleagues, students.
- **The same place looks the same** in every scene set there (colours, furniture, people).

To choose looks yourself, edit `storyboard.json`:

```json
"hero_look": {"hair_style": "hijab", "hijab": "#1d3557", "glasses": true},
"cast": [
  {"name": "করিম", "type": "man", "outfit": "shopkeeper",
   "look": {"beard": "beard", "tupi": true, "build": "heavy"}}
],
```

and put `"with": "করিম"` in a scene to show him there. Look options: `hair_style` (short, side,
spiky, curly, long, bun, ponytail, hijab), `hijab` (a colour), `beard` (beard, mustache), `tupi`,
`glasses` (true/false), `build` (slim, normal, heavy), `skin`, `shirt`, `pants`, `hair` (colours).

---

## Speed

| style / quality | 50-second video on a normal laptop |
|---|---|
| footage | ~3–5 min |
| 3d, draft | ~15 min |
| 3d, standard | ~40 min |
| 3d, high | ~2 h |

The AI script adds about 5–10 minutes per topic. With 3D, queue several topics overnight, e.g.
`--next 5`.

---

## Troubleshooting

Run `python make_video.py --doctor` first: it tells you what's missing and how to fix it.

| problem | fix |
|---|---|
| "No footage source set up" | add a free Pexels/Pixabay key (setup.bat), or use `--style 3d` |
| voice: "No audio was received" | a hiccup at the free voice service; run the command again |
| YouTube: `youtubeSignupRequired` | the Google account has no channel: create one, then `--login youtube` again |
| YouTube videos stay private | new Google API projects must pass a free audit first (PUBLISHING.md) |
| TikTok posts are private | TikTok must approve your app first; or use `TIKTOK_MODE=draft` |
| the AI wrote something wrong | edit `narration` in `storyboard.json` and run the topic again |
| Bangla shows as boxes in the console | use `start.bat` (it switches the console to UTF-8) |

---

## For developers

```
make_video.py           command line / orchestration (make_3d_video.py = old name, still works)
setup.bat, start.bat    double-click setup and menu
factory/topics.py       reads topics.txt and topics/*.txt, language detection
factory/storyboard.py   AI script (plain text) + scene plan (JSON schema), keyword fallback
factory/casting.py      makes the actor (age, outfit, action) match every line
factory/voice.py        edge-tts per scene with word timings, padded narration track
factory/captions.py     word-highlighted captions, title banner, outro
factory/footage.py      real footage: own clips, Pexels, Pixabay; search, download, cut
factory/render.py       frame timeline, Blender job, resumable rendering
factory/compose.py      ffmpeg crossfades, upscale, captions, music, loudness
factory/publish.py      YouTube / Facebook / TikTok upload + logins
factory/history.py      history of everything made and posted
factory/setup.py        --setup wizard, --doctor, Blender download
factory/vocab.py        the scene vocabulary shared by the AI planner and Blender
blender/                scene builder run inside Blender (worlds, props, character, kit)
```

**Adding a prop:** describe it in `factory/vocab.py`, then write a function with the same name in
`blender/props.py` that returns `Built(root, height, width)`. Blender refuses to start if a prop
has no builder.

**Manual install** (instead of setup.bat): `python -m venv venv`, then
`venv\Scripts\pip install -r requirements.txt`, then `winget install Gyan.FFmpeg Ollama.Ollama`,
then `ollama pull gemma4:26b` (or a smaller model, see "Which AI model"), then
`python make_video.py --setup`.

`generate_video.py` is the original single-picture version and still works.
