# Real footage + uploading to YouTube, Facebook and TikTok

Everything here is set up once. Afterwards a single command makes the next video and posts it:

```powershell
python make_video.py --next --upload youtube,facebook,tiktok
```

First copy `.env.example` to `.env`. All keys go into `.env`, and the upload logins are saved in
`credentials/`. Git ignores both.

---

## 1. Real video footage (Pexels and Pixabay, free)

Each narration line gets a real video clip. The AI writes an English search phrase for every
scene (you can see and edit it as `"footage"` in `storyboard.json`). The program then finds a
vertical clip, downloads it once, and cuts it to the exact length of that line.

1. **Pexels:** sign up at <https://www.pexels.com/api/>, copy *Your API key*, then put
   `PEXELS_API_KEY=...` in `.env`.
2. **Pixabay** (more clips): log in at <https://pixabay.com/api/docs/>. Your key appears on that
   page. Put `PIXABAY_API_KEY=...` in `.env`.

Both libraries are free and licensed for commercial use (monetised pages are fine). Footage
credits are added to each video's description anyway.

**Your own clips:** put `.mp4` files in `assets/footage/` and name them with the words they show,
e.g. `shopkeeper-grocery-store-bangladesh.mp4` or `rickshaw-dhaka-street.mp4`. Your clips are
used before stock footage whenever the words match. This is the best way to get local Bangladeshi
scenes, which stock sites have few of.

**Why not YouTube clips?** Other people's YouTube videos are copyrighted, and downloading them
breaks YouTube's terms. Re-uploading them gets Content ID claims and copyright strikes, and can
get your Page or channel removed.

Switch between styles with `--style footage` / `--style 3d`, or set `VIDEO_STYLE` in `.env`.

---

## 2. YouTube (uploads as Shorts)

1. Go to <https://console.cloud.google.com/> and create a project.
2. *APIs & Services → Library*: enable **YouTube Data API v3**.
3. *APIs & Services → OAuth consent screen*: choose External, fill in the app name and your email,
   and add yourself under **Test users**.
4. *APIs & Services → Credentials → Create credentials → OAuth client ID → Desktop app*.
   Download the JSON and save it as `credentials/youtube_client_secret.json`.
5. Run `python make_video.py --login youtube`. A browser opens: pick the channel and allow access.

**Important limits (set by Google, not by this program):**
- **Private until audited:** videos uploaded through a new, unaudited API project are locked to
  *private*. To post publicly, submit the free *YouTube API Services Audit and Quota Extension*
  form for your project. Until then, upload privately and publish them yourself from YouTube
  Studio after approval.
- **About 6 uploads per day:** the default quota is 10,000 units and each upload costs 1,600.

---

## 3. Facebook Page (uploads as Reels)

1. Go to <https://developers.facebook.com/apps/>, then *Create app → Other → Business*.
2. Copy *App ID* and *App secret* (*App settings → Basic*) into `.env` as `FACEBOOK_APP_ID` and
   `FACEBOOK_APP_SECRET`.
3. Run `python make_video.py --login facebook` and follow the three steps it prints. You'll
   generate a token in the Graph API Explorer with the permissions `pages_show_list`,
   `pages_read_engagement` and `pages_manage_posts`, then paste it.
4. If you manage several Pages, it asks which one to use. The saved Page token does not expire.

The app can stay in *Development* mode: you are its admin, so it may post to your own Page.

---

## 4. TikTok

1. Go to <https://developers.tiktok.com/>, register, then *Manage apps → Connect an app*.
2. Add the products **Login Kit** and **Content Posting API**. In Login Kit, add the redirect URI
   `http://localhost:8723/callback/` (Desktop). Enable the scopes `user.info.basic`,
   `video.publish` and `video.upload`.
3. Put the *Client key* and *Client secret* in `.env` as `TIKTOK_CLIENT_KEY` and
   `TIKTOK_CLIENT_SECRET`.
4. Run `python make_video.py --login tiktok`. Log in in the browser window and allow access.

**Important limits (set by TikTok):**
- **Private until audited:** until your app passes TikTok's review, posts can only be *private*
  (only you can see them). The program then posts as private automatically. After approval,
  `TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE` works.
- **Draft mode:** set `TIKTOK_MODE=draft` and the video lands in your TikTok inbox. You add sounds
  and post it from the app yourself.
- **Re-login:** the login lasts a year; after that, run `--login tiktok` again.

---

## Day-to-day

Set `AUTO_UPLOAD=youtube,facebook` (or let `setup.bat` do it), and every new video is posted as
soon as it is finished:

```powershell
python make_video.py --next                                  # make the next topic, post it automatically
python make_video.py --next --no-upload                      # make it, but don't post this time
python make_video.py --upload-existing                       # post finished videos that aren't posted yet
python make_video.py --upload-existing --upload facebook     # ... only to Facebook
python make_video.py --history                               # what was posted where (+ output/history.csv)
```

- `output/<topic>/post.json` holds the title, description and hashtags. It's written once; edit it
  before uploading if you like.
- `output/<topic>/uploads.json` remembers where each video went, so nothing is posted twice.
  Delete a platform's entry to post it again.
- If one platform fails, the others still upload. Fix the problem and run the same command again.
- If a platform's daily limit is hit (e.g. YouTube), the remaining videos simply go up on the next run.
