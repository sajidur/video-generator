"""Upload finished videos to YouTube (Shorts), a Facebook Page (Reels) and TikTok.

One-time setup per platform: see PUBLISHING.md, then  python make_3d_video.py --login <platform>
Per video:
  output/<topic>/post.json     title, description, tags (written once, edit it freely)
  output/<topic>/uploads.json  what was uploaded where (so nothing is posted twice)
"""
import hashlib
import http.server
import json
import secrets
import threading
import time
import urllib.parse
import webbrowser

import requests

from . import config, history

PLATFORMS = ("youtube", "facebook", "tiktok")
TIKTOK_API = "https://open.tiktokapis.com/v2"


def _short(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1].rsplit(" ", 1)[0] + "…"


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


# ---------------------------------------------------------------- metadata ---

TAG_RULES = [  # (words to look for, hashtags to add)
    (("মার্কেটিং", "marketing"), ["#মার্কেটিং", "#Marketing"]),
    (("ব্যবসা", "business"), ["#ব্যবসা", "#Business"]),
    (("কটলার", "kotler"), ["#PhilipKotler", "#PrinciplesOfMarketing"]),
    (("গ্রাহক", "customer"), ["#Customer"]),
    (("দাম", "price", "pricing"), ["#Pricing"]),
    (("ব্র্যান্ড", "brand"), ["#Branding"]),
    (("বিজ্ঞাপন", "advertis"), ["#Advertising"]),
    (("সোশ্যাল মিডিয়া", "social media", "ডিজিটাল", "digital"), ["#DigitalMarketing"]),
]


def display_title(board):
    """The video's title without a trailing source ("— ... book") part (the source goes in the description)."""
    title = board.get("title") or board.get("topic", "")
    head, sep, tail = title.rpartition(" — ")
    if sep and ("বই" in tail or "book" in tail.lower()):
        title = head
    return " ".join(title.split())


def make_post(board, credits, out):
    """Title, description and hashtags for all platforms. Saved once; edit post.json to change it."""
    path = out / "post.json"
    if path.exists():
        return _load_json(path)
    lang = board.get("lang", "en")
    lines = [s["narration"] for s in board["shots"]]
    text = (board.get("topic", "") + " " + " ".join(lines)).lower()
    hashtags = ["#Shorts"] + (["#বাংলা"] if lang == "bn" else [])
    for words, tags in TAG_RULES:
        if any(w in text for w in words):
            hashtags += [t for t in tags if t not in hashtags]
    parts = [" ".join(lines)]
    if "কটলার" in text or "kotler" in text:
        parts.append(("সূত্র: " if lang == "bn" else "Source: ") +
                     "Philip Kotler & Gary Armstrong, Principles of Marketing")
    names = sorted({c["credit"] for c in credits if c.get("credit")})
    if names:
        parts.append(("ফুটেজ: " if lang == "bn" else "Footage: ") + ", ".join(names))
    parts.append(" ".join(hashtags[:12]))
    title = _short(display_title(board), 95)
    post = {"title": title, "description": "\n\n".join(parts),
            "tags": [t.lstrip("#") for t in hashtags if t != "#Shorts"], "hashtags": hashtags}
    _save_json(path, post)
    return post


# ----------------------------------------------------------------- youtube ---

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _youtube_credentials(login=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    token = config.CREDENTIALS / "youtube_token.json"
    secret = config.CREDENTIALS / "youtube_client_secret.json"
    creds = Credentials.from_authorized_user_file(str(token), YT_SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if login or not creds or not creds.valid:
        if not login:
            raise RuntimeError("YouTube is not connected. Run:  python make_3d_video.py --login youtube")
        if not secret.exists():
            raise RuntimeError(f"Save your Google OAuth client file as {secret} first (see PUBLISHING.md)")
        creds = InstalledAppFlow.from_client_secrets_file(str(secret), YT_SCOPES).run_local_server(
            port=0, prompt="consent")
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload_youtube(video, post, lang, log):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=_youtube_credentials(), cache_discovery=False)
    privacy = config.env("YOUTUBE_PRIVACY", "public")
    body = {
        "snippet": {"title": _short(post["title"], 100).replace("<", "").replace(">", ""),
                    "description": post["description"][:4900], "tags": post.get("tags", [])[:15],
                    "categoryId": config.env("YOUTUBE_CATEGORY", "27"),  # 27 = Education
                    "defaultLanguage": lang, "defaultAudioLanguage": lang},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(
        str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            log(f"    youtube upload {int(status.progress() * 100)}%")
    return {"id": resp["id"], "url": f"https://youtube.com/shorts/{resp['id']}", "privacy": privacy}


# ---------------------------------------------------------------- facebook ---


def _graph():
    return f"https://graph.facebook.com/{config.env('FACEBOOK_GRAPH_VERSION', 'v23.0')}"


def _fb_json(r):
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or "error" in data:
        msg = (data.get("error") or {}).get("message") or r.text[:300]
        raise RuntimeError(f"Facebook: {msg}")
    return data


def _facebook_page():
    saved = _load_json(config.CREDENTIALS / "facebook.json", {}) or {}
    page_id = saved.get("page_id") or config.env("FACEBOOK_PAGE_ID")
    token = saved.get("page_token") or config.env("FACEBOOK_PAGE_TOKEN")
    if not (page_id and token):
        raise RuntimeError("Facebook is not connected. Run:  python make_3d_video.py --login facebook")
    return page_id, token


def login_facebook(log):
    app_id, app_secret = config.env("FACEBOOK_APP_ID"), config.env("FACEBOOK_APP_SECRET")
    if not (app_id and app_secret):
        raise RuntimeError("Set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in .env first (see PUBLISHING.md)")
    log("1. Open https://developers.facebook.com/tools/explorer/ and pick your app.")
    log("2. Add permissions: pages_show_list, pages_read_engagement, pages_manage_posts")
    log("3. Click 'Generate Access Token', allow your Page, then copy the token.")
    short = input("Paste the user access token here: ").strip()
    long_user = _fb_json(requests.get(f"{_graph()}/oauth/access_token", timeout=30, params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
        "fb_exchange_token": short}))["access_token"]
    pages = _fb_json(requests.get(f"{_graph()}/me/accounts", timeout=30, params={
        "access_token": long_user, "fields": "id,name,access_token"})).get("data", [])
    if not pages:
        raise RuntimeError("No Facebook Pages found for this account / token.")
    want = config.env("FACEBOOK_PAGE_ID")
    page = next((p for p in pages if p["id"] == want), None)
    if not page:
        for i, p in enumerate(pages, 1):
            log(f"   {i}. {p['name']} ({p['id']})")
        page = pages[int(input("Which page number? ").strip() or "1") - 1] if len(pages) > 1 else pages[0]
    _save_json(config.CREDENTIALS / "facebook.json",
               {"page_id": page["id"], "page_name": page["name"], "page_token": page["access_token"]})
    log(f"Facebook connected: {page['name']} (the page token does not expire)")


def upload_facebook(video, post, lang, log):
    page_id, token = _facebook_page()
    start = _fb_json(requests.post(f"{_graph()}/{page_id}/video_reels", timeout=60,
                                   data={"upload_phase": "start", "access_token": token}))
    vid = start["video_id"]
    size = video.stat().st_size
    with open(video, "rb") as f:
        _fb_json(requests.post(start["upload_url"], data=f, timeout=900, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)}))
    _fb_json(requests.post(f"{_graph()}/{page_id}/video_reels", timeout=60, data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "access_token": token,
        "description": (post["title"] + "\n\n" + post["description"])[:2200]}))
    for _ in range(36):  # wait up to 3 minutes for Facebook to process it
        st = requests.get(f"{_graph()}/{vid}", timeout=30,
                          params={"fields": "status", "access_token": token}).json().get("status", {})
        if st.get("video_status") == "error":
            raise RuntimeError(f"Facebook processing failed: {st}")
        if (st.get("publishing_phase") or {}).get("status") == "complete" or st.get("video_status") == "ready":
            break
        time.sleep(5)
    return {"id": vid, "url": f"https://www.facebook.com/reel/{vid}"}


# ------------------------------------------------------------------ tiktok ---


def _tiktok_token_request(data):
    r = requests.post(f"{TIKTOK_API}/oauth/token/", data=data, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    tok = r.json()
    if "access_token" not in tok:
        raise RuntimeError(f"TikTok login failed: {tok}")
    now = time.time()
    tok["expires_at"] = now + int(tok.get("expires_in", 0)) - 120
    tok["refresh_expires_at"] = now + int(tok.get("refresh_expires_in", 0))
    _save_json(config.CREDENTIALS / "tiktok.json", tok)
    return tok


def _tiktok_access_token():
    tok = _load_json(config.CREDENTIALS / "tiktok.json")
    if not tok:
        raise RuntimeError("TikTok is not connected. Run:  python make_3d_video.py --login tiktok")
    if time.time() < tok.get("expires_at", 0):
        return tok["access_token"]
    if time.time() > tok.get("refresh_expires_at", 0):
        raise RuntimeError("TikTok login expired. Run:  python make_3d_video.py --login tiktok")
    return _tiktok_token_request({
        "client_key": config.env("TIKTOK_CLIENT_KEY"), "client_secret": config.env("TIKTOK_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})["access_token"]


def login_tiktok(log):
    key, secret = config.env("TIKTOK_CLIENT_KEY"), config.env("TIKTOK_CLIENT_SECRET")
    redirect = config.env("TIKTOK_REDIRECT_URI", "http://localhost:8723/callback/")
    if not (key and secret):
        raise RuntimeError("Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in .env first (see PUBLISHING.md)")
    verifier = secrets.token_urlsafe(64)[:64]
    state = secrets.token_urlsafe(16)
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
        "client_key": key, "response_type": "code", "scope": "user.info.basic,video.publish,video.upload",
        "redirect_uri": redirect, "state": state,
        "code_challenge": hashlib.sha256(verifier.encode()).hexdigest(),  # TikTok desktop PKCE: hex SHA-256
        "code_challenge_method": "S256"})
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("TikTok connected. You can close this window.".encode())

        def log_message(self, *args):
            pass

    port = urllib.parse.urlparse(redirect).port or 80
    server = http.server.HTTPServer(("localhost", port), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    log("A browser window opens: log in to TikTok and allow access ...")
    webbrowser.open(url)
    for _ in range(300):
        if got:
            break
        time.sleep(1)
    server.server_close()
    if got.get("state") != state or "code" not in got:
        raise RuntimeError(f"TikTok login was not completed: {got or 'timed out'}")
    _tiktok_token_request({"client_key": key, "client_secret": secret, "code": got["code"],
                           "grant_type": "authorization_code", "redirect_uri": redirect,
                           "code_verifier": verifier})
    log("TikTok connected.")


def _tt(path, token, body):
    r = requests.post(f"{TIKTOK_API}{path}", json=body, timeout=60, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    data = r.json()
    err = data.get("error") or {}
    if err.get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok: {err.get('code')}: {err.get('message')}")
    return data.get("data") or {}


def upload_tiktok(video, post, lang, log):
    token = _tiktok_access_token()
    size = video.stat().st_size
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    count = max(1, size // chunk)
    source = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}
    draft = config.env("TIKTOK_MODE", "direct") == "draft"
    privacy = "draft"
    if draft:  # lands in your TikTok inbox; you press "post" in the app
        init = _tt("/post/publish/inbox/video/init/", token, {"source_info": source})
    else:
        options = _tt("/post/publish/creator_info/query/", token, {}).get("privacy_level_options", [])
        want = config.env("TIKTOK_PRIVACY", "PUBLIC_TO_EVERYONE")
        privacy = want if want in options else ("SELF_ONLY" if "SELF_ONLY" in options else (options or [want])[0])
        if privacy != want:
            log(f"    TikTok only allows {options} for this app right now -> posting as {privacy}")
        caption = _short(post["title"] + " " + " ".join(post.get("hashtags", [])), 2200)
        init = _tt("/post/publish/video/init/", token, {"source_info": source, "post_info": {
            "title": caption, "privacy_level": privacy, "disable_duet": False, "disable_comment": False,
            "disable_stitch": False, "video_cover_timestamp_ms": 1000}})
    with open(video, "rb") as f:
        for i in range(count):
            start = i * chunk
            data = f.read(chunk if i < count - 1 else size - start)
            end = start + len(data) - 1
            r = requests.put(init["upload_url"], data=data, timeout=600, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code >= 400:
                raise RuntimeError(f"TikTok upload failed ({r.status_code}): {r.text[:200]}")
    status = "?"
    for _ in range(60):
        st = _tt("/post/publish/status/fetch/", token, {"publish_id": init["publish_id"]})
        status = st.get("status", "?")
        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            break
        if status == "FAILED":
            raise RuntimeError(f"TikTok rejected the video: {st.get('fail_reason')}")
        time.sleep(5)
    return {"id": init["publish_id"], "status": status, "privacy": privacy,
            "url": "TikTok inbox (open the app to post)" if draft else "https://www.tiktok.com/"}


# -------------------------------------------------------------------- main ---

UPLOADERS = {"youtube": upload_youtube, "facebook": upload_facebook, "tiktok": upload_tiktok}
LOGINS = {"youtube": lambda log: (_youtube_credentials(login=True), log("YouTube connected.")),
          "facebook": login_facebook, "tiktok": login_tiktok}


def login(platform, log=print):
    LOGINS[platform](log)


_blocked = {}  # platform -> reason; set when a daily limit is hit, so later videos wait for the next run


def upload(out, video, platforms, log=print):
    """Upload one finished video to the given platforms (skips ones already done)."""
    board = _load_json(out / "storyboard.json")
    credits = _load_json(out / "credits.json", [])
    post = make_post(board, credits, out)
    record = out / "uploads.json"
    done = _load_json(record, {})
    for p in platforms:
        if p in done:
            log(f"  {p}: already uploaded -> {done[p].get('url')}")
            continue
        if p in _blocked:
            log(f"  {p}: skipped ({_blocked[p]}); it will be uploaded on a later run")
            continue
        log(f"  uploading to {p} ...")
        try:
            info = UPLOADERS[p](video, post, board.get("lang", "en"), log)
        except Exception as exc:  # one platform failing must not stop the others
            text = str(exc)
            if any(k in text for k in ("quotaExceeded", "uploadLimitExceeded", "rateLimitExceeded",
                                       "spam_risk", "too many")):
                _blocked[p] = "daily upload limit reached"
            if "not connected" in text or "expired" in text:
                _blocked[p] = "account not connected"
            if "youtubeSignupRequired" in text:
                _blocked[p] = "no YouTube channel on the connected Google account"
                text = ("the Google account you connected has no YouTube channel. Create one at "
                        "https://www.youtube.com/create_channel (or pick the account / brand account that "
                        "owns your channel), then run:  python make_3d_video.py --login youtube")
            log(f"  {p} FAILED: {text}")
            continue
        info["time"] = time.strftime("%Y-%m-%d %H:%M")
        done[p] = info
        _save_json(record, done)
        history.add("uploaded", slug=out.name, platform=p, url=info.get("url", ""),
                    privacy=info.get("privacy", ""))
        log(f"  {p}: done -> {info.get('url')}")
    return done
