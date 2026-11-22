"""Blender entry point: renders every shot of one storyboard to PNG frames.

    blender -b --factory-startup -P blender/shot.py -- <render_job.json> [--still]

Shots whose folder already has done.json are skipped, and finished frames are
never re-rendered, so an interrupted render continues where it stopped.
--still renders one preview frame per shot (for checking a storyboard fast).
"""
import json
import math
import random
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import character  # noqa: E402
import kit as K  # noqa: E402
import props as P  # noqa: E402
import worlds  # noqa: E402
from factory import vocab  # noqa: E402

LENS = 30.0
SENSOR = 36.0


class Ctx:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Focus:
    def __init__(self, center, radius, track=None):
        self.center = Vector(center)
        self.radius = radius
        self.track = track


# ------------------------------------------------------------------ layout ---

BIG_SPOTS = {"mountain": (32, 1.0), "volcano": (20, 0.9), "pyramid": (15, 1.0), "buildings": (15, 1.0)}
SELF_ANIMATED = {"coins", "books", "bar_chart", "stairs", "flowers", "phone", "laptop", "crowd", "car",
                 "rocket", "boat", "wind_turbine", "person", "truck", "rickshaw", "boxes", "produce",
                 "shopping_bag", "billboard", "whiteboard", "down_chart"}
VEHICLES = {"car", "truck", "rickshaw"}            # drive past behind the actor, never through them
BACKDROPS = {"billboard", "shopfront", "whiteboard", "tv"}  # tall things: stand behind the actor
# how far the actor turns towards the other person / thing (1 = face them fully)
TURN = {"shake_hands": 1.0, "give": 0.6, "buy": 0.6, "listen": 0.55, "talk": 0.45, "point": 0.45,
        "announce": 0.35, "thumbs_up": 0.35}
# where the other person stands (relative to the actor) for close interactions
PARTNER_SPOT = {"shake_hands": (1.15, 0.0), "give": (1.3, 0.1), "buy": (1.3, 0.1)}
FACING = {"walk": 1.15, "run": 1.2, "carry": 1.15, "push_cart": 1.15, "think": 0.3, "read": 0.15,
          "phone": 0.25, "write": 0.2, "drink": 0.3, "search": 0.0}


def layout(shot, env, c, hero):
    props = [p for p in shot.get("props", []) if p in P.REGISTRY][:3]
    action = shot.get("character", "none")
    if action not in vocab.ACTIONS:
        action = "idle"
    c.hero_action = action  # the other person and the crowd react to it
    if "person" in props and action in TURN:  # the person the actor deals with stands right next to them
        props.remove("person")
        props.insert(0, "person")
    kind = {p: vocab.prop_kind(p) for p in props}
    stage = [p for p in props if kind[p] in ("icon", "ground")]
    bigs = [p for p in props if kind[p] == "big"]
    skies = [p for p in props if kind[p] == "sky"]
    has_char = action != "none"
    focus = []
    ground = env.ground
    space = env.name == "space"

    # a sky object becomes the hero when nothing else is on stage
    if not has_char and not stage and not bigs and skies:
        stage.append(skies.pop(0))
    if not has_char and not stage and not bigs:
        has_char, action = True, "idle"

    char_h = 0.0
    char_track = None
    ch = None
    walking = action in ("walk", "run", "carry", "push_cart") and not space
    c.work_mode = "type" if {"laptop", "phone"} & set(props) else ""
    if has_char:
        cx = -0.55 if stage else 0.0
        facing = FACING.get(action, c.rng.uniform(-0.3, 0.3))
        z = 0.4 if space else ground(cx, 0)
        ch = character.build(hero, c, loc=(cx, 0, z), astronaut=space, outfit=hero.get("outfit"))
        if space:
            K.bob(ch["root"], 0.12, 0.18)
            K.sway(ch["root"], 0.08, 0.12, 1)
        track = character.act(ch, action, c, phase=c.rng.uniform(0, 3), facing=facing,
                              travel=not space)
        char_h = ch["height"]
        char_track = track if walking else None
        focus.append(Focus((cx, 0, z + char_h * 0.5), char_h * 0.55, track))

    if walking:  # keep the walking path clear
        side_slots = [(1.1, 2.6), (-2.2, 3.0), (2.8, 3.4)]
    elif has_char:
        side_slots = [(0.85, 0.45), (-1.3, 1.9), (1.4, 2.2)]
    else:  # vertical frame: stack extra items in depth, not width
        side_slots = [(0.0, 0.0), (-1.05, 1.6), (1.1, 1.9)]
    for i, name in enumerate(stage):
        b = P.REGISTRY[name](c)
        x, y = side_slots[min(i, 2)]
        k = kind[name]
        if k == "icon" or k == "sky":
            follow = False
            if has_char and i == 0:
                cx = -0.55
                x, y = cx + 1.25, -0.15
                z = (0.4 if space else ground(cx, 0)) + char_h * 0.92
                s = 0.7
                follow = char_track is not None
            else:
                s = 1.0 if i == 0 else 0.75
                z = (1.5 if k == "icon" else 1.9) + (0.0 if space else ground(x, y))
                if i > 0 and not has_char:
                    z += 0.9
                if k == "sky":
                    s = 1.25
            b.root.location = (x, y, z)
            b.root.scale = (s, s, s)
            K.bob(b.root, 0.08, 0.35, i * 1.3)
            K.pop(b.root, delay=c.t0 + 0.15 + 0.2 * i, dur=0.7)
            if follow:
                K.animate(b.root, lambda t, st, tr=char_track: st.loc.__iadd__(tr(t)))
            focus.append(Focus((x, y, z), max(b.height, b.width) * 0.5 * s))
        else:
            s = 1.0 if i == 0 or not has_char else 0.85
            if has_char and name in VEHICLES:
                x, y = (0.4, 2.9) if i == 0 else (0.0, 4.2)
            elif has_char and name in BACKDROPS:
                x, y = (0.95, 2.3) if i == 0 else (-1.6, 2.8)
            elif name == "person" and ch and i == 0 and action in PARTNER_SPOT:
                dx, dy = PARTNER_SPOT[action]
                x, y = ch["root"].location.x + dx, dy
            z = (0.0 if not space else -0.5) + ground(x, y)
            if env.water is not None and name == "boat":
                x, y, z = (2.6, 2.0, env.water)
            b.root.location = (x, y, z)
            b.root.scale = (s, s, s)
            if name == "person" and ch:  # turn to the hero (3/4 view so the face stays visible)
                hx, hy = ch["root"].location.x, ch["root"].location.y
                k = 1.0 if action == "shake_hands" else 0.7
                b.root.rotation_euler.z = k * math.atan2(hx - x, -(hy - y))
            if name not in SELF_ANIMATED:
                K.pop(b.root, delay=c.t0 + 0.1 + 0.2 * i, dur=0.7)
            focus.append(Focus((x, y, z + b.height * 0.5 * s), max(b.height, b.width) * 0.5 * s))

    # the hero turns towards whoever / whatever they talk to, point at or deal with
    turn = TURN.get(action, 0.45 if action == "work" and c.work_mode == "type" else 0.0)
    if ch and turn and len(focus) > 1:
        tx, ty = focus[1].center.x, focus[1].center.y
        hx, hy = ch["root"].location.x, ch["root"].location.y
        ch["root"].rotation_euler.z = turn * math.atan2(tx - hx, -(ty - hy))

    hero_big = not focus
    for i, name in enumerate(bigs):
        b = P.REGISTRY[name](c)
        y, s = BIG_SPOTS[name]
        x = (0, -9, 9)[i]
        if hero_big:
            y *= 0.6
        b.root.location = (x, y, ground(x, y) - 0.3)
        b.root.scale = (s, s, s)
        if hero_big and i == 0:  # a landmark only becomes the subject when nothing else is
            focus.append(Focus((x, y, b.height * s * 0.45), b.width * s * 0.4))

    if space:
        sky_spots = [(-2.6, 8, 3.4), (3.0, 11, 4.6), (0.4, 14, 6.0)]
    else:
        sky_spots = [(-3.2, 18, 8.0), (3.8, 22, 9.5), (0.5, 26, 11)]
    for i, name in enumerate(skies):
        b = P.REGISTRY[name](c)
        x, y, z = sky_spots[i]
        s = {"sun": 1.6, "moon": 1.3, "planet": 1.4, "earth": 1.4, "clouds": 0.8, "birds": 1.0,
             "airplane": 1.2}.get(name, 1.0)
        if name in ("birds", "airplane"):
            speed = 1.3 if name == "birds" else 2.0
            x = -speed * c.dur / 2
            y, z = 12, 6.5
        if name == "clouds":
            x, y, z = 0, 24, 8
        b.root.location = (x, y, z)
        b.root.scale = (s, s, s)
    return focus, char_h


def frame_focus(focus, aspect):
    if not focus:
        focus = [Focus((0, 0, 1), 1.5)]
    center = sum((f.center for f in focus), Vector()) / len(focus)
    radius = max((f.center - center).length + f.radius for f in focus)
    half_w = math.atan((SENSOR / 2) * min(1.0, aspect) / LENS)
    half_h = math.atan((SENSOR / 2) * min(1.0, 1 / aspect) / LENS)
    dist = max(3.2, radius / math.tan(half_w) * 1.12, radius / math.tan(half_h) * 1.15)
    track = next((f.track for f in focus if f.track), None)
    return center, radius, dist, track


# ------------------------------------------------------------------ camera ---


def camera_rig(move, focus, env, c, aspect, dof):
    center, radius, D, track = frame_focus(focus, aspect)
    cam = K.link(bpy.data.objects.new("camera", bpy.data.cameras.new("camera")))
    cam.data.lens = LENS
    cam.data.sensor_width = SENSOR
    cam.data.sensor_fit = "AUTO"
    cam.data.clip_start = 0.1
    cam.data.clip_end = 800
    cam.data.dof.use_dof = dof
    cam.data.dof.aperture_fstop = 3.2
    K.scene().camera = cam
    a0 = c.rng.uniform(-0.3, 0.3)
    dur = c.dur
    if move not in vocab.CAMERAS:
        move = "push_in"

    def target(t):
        p = center.copy()
        if track:
            p += track(t) * 0.85
        return p

    def pose(t):
        u = K.smooth(t / dur)
        tgt = target(t)
        a, d, h = a0, D, D * 0.2
        if move == "orbit":
            a = a0 - 0.4 + 0.8 * u
        elif move == "push_in":
            d = D * (1.3 - 0.38 * u)
        elif move == "pull_out":
            d = D * (0.85 + 0.5 * u)
            h = D * (0.15 + 0.18 * u)
        elif move == "pan":
            a = a0 + 0.12 * (u - 0.5)
            side = Vector((math.cos(a), math.sin(a), 0)) * D * 0.35 * (u - 0.5)
            tgt = tgt + side * 0.6
        elif move == "crane_up":
            h = D * (0.02 + 0.7 * u)
            d = D * (1.05 - 0.1 * u)
        elif move == "low_angle":
            h = 0.35 - tgt.z
            d = D * (1.05 - 0.15 * u)
            tgt = tgt + Vector((0, 0, 0.35))
        elif move == "fly_over":
            d = D * (2.3 - 1.25 * u)
            h = D * (1.1 - 0.9 * u)
        pos = tgt + Vector((math.sin(a) * d, -math.cos(a) * d, h))
        if move == "pan":
            pos += Vector((math.cos(a), math.sin(a), 0)) * D * 0.35 * (u - 0.5)
        pos += Vector((K.wobble(t, 1.1, 0.3), K.wobble(t, 2.2, 0.3), K.wobble(t, 3.3, 0.3))) * 0.012 * D
        floor = env.water if env.water is not None else env.ground(pos.x, pos.y)
        if not env.floating:
            pos.z = max(pos.z, floor + 0.3)
        return pos, tgt

    def update(t):
        pos, tgt = pose(t)
        cam.location = pos
        K.look_at(cam, tgt)
        cam.data.dof.focus_distance = (tgt - pos).length
    K.every_frame(update)
    return cam, center, radius, D


def stage_lights(env, center, D):
    """Rim light behind the subject + soft key from the camera side (readable faces)."""
    if env.name == "room":
        return
    k = max(1.0, D / 7) ** 2
    rim = {"sunset": "#ffb38a", "sunrise": "#ffd1a1", "night": "#8fb0ff"}.get(env.time, "#ffffff")
    K.light("AREA", 450 * k, rim, loc=center + Vector((0.5, 4.0, 3.2)), target=center, size=3.0, shadow=False)
    if env.name == "studio":
        return
    key = {"night": ("#b8c8ff", 420), "sunset": ("#ffd9c2", 380), "sunrise": ("#ffe3c8", 330)}.get(
        env.time, ("#fff6ea", 200))
    K.light("AREA", key[1] * k, key[0], loc=center + Vector((-2.8, -6.0, 3.8)), target=center, size=5.0,
            shadow=False)


def title(text, c, cam, center, radius, D, top_z, aspect):
    text = " ".join(str(text).split())[:40]
    if not text:
        return
    words = text.split()
    if len(text) > 14 and len(words) > 1:
        best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(text) / 2))
        text = " ".join(words[:best]) + "\n" + " ".join(words[best:])
    z = max(top_z + 0.5, center.z + radius * 0.9)
    root = K.empty("title", loc=(center.x, center.y + 0.3, z), rot=(math.pi / 2, 0, 0))
    front = K.text3d(text.upper(), size=0.5, depth=0.06, color=c.accent, kind="emit", emit=1.2,
                     fontfile=c.font_bold, parent=root, rot=(0, 0, 0))
    back = K.text3d(text.upper(), size=0.5, depth=0.05, color="#14122b", kind="gloss",
                    fontfile=c.font_bold, parent=root, loc=(0.0, -0.012, -0.07), rot=(0, 0, 0))
    back.data.offset = 0.035
    bpy.context.view_layer.update()
    width = max(back.dimensions.x, 1e-3)
    half_w = math.atan((SENSOR / 2) * min(1.0, aspect) / LENS)
    visible = 2 * D * 1.05 * math.tan(half_w)
    s = min(1.6, visible * 0.8 / width)
    root.scale = (s, s, s)
    con = root.constraints.new("DAMPED_TRACK")
    con.target = cam
    con.track_axis = "TRACK_Z"
    K.pop(root, delay=c.t0 + 0.2, dur=0.7)
    K.bob(root, 0.05, 0.3)


# ------------------------------------------------------------------ render ---


def _clean_partial_frames(out):
    for p in out.glob("*.png"):
        try:
            with open(p, "rb") as f:
                f.seek(max(0, p.stat().st_size - 16))
                ok = b"IEND" in f.read()
        except OSError:
            ok = False
        if not ok:
            p.unlink(missing_ok=True)


def build_shot(job, shot):
    K.reset()
    fps = job["fps"]
    seed = int(shot["seed"])
    rng = random.Random(seed)
    frames = int(shot["frames"])
    c = Ctx(rng=rng, seed=seed, night=shot.get("time") == "night", accent=shot.get("accent", "#ffd166"),
            dur=frames / fps, t0=float(shot.get("head", 0.0)), font_bold=job.get("font_bold"),
            props=list(shot.get("props", [])))
    K.setup_render(job["width"], job["height"], fps, job["samples"], job["quality"])
    env = worlds.build(shot.get("environment", "studio"), shot.get("time", "day"), c)
    h = job.get("hero", {})
    # same seed in every shot = same face and colours; the form (age) and outfit can change per shot
    hero = character.random_look(random.Random(h.get("seed", 0)), shot.get("hero") or h.get("type", "boy"))
    hero.update({k: v for k, v in h.items() if k in hero and k != "type"})
    hero["outfit"] = shot.get("outfit", "casual")
    focus, char_h = layout(shot, env, c, hero)
    aspect = job["width"] / job["height"]
    cam, center, radius, D = camera_rig(shot.get("camera", "push_in"), focus, env, c, aspect,
                                        dof=job["quality"] != "draft")
    stage_lights(env, center, D)
    if job.get("titles", True) and shot.get("title_3d"):
        top = max((f.center.z + f.radius for f in focus), default=2.0)
        title(shot["title_3d"], c, cam, center, radius, D, top, aspect)
    sc = K.scene()
    sc.frame_start, sc.frame_end = 1, frames
    K.install_frame_handler(fps)
    return sc, frames


def render_job(job, still=False):
    shots = job["shots"]
    for shot in shots:
        out = Path(shot["out_dir"])
        out.mkdir(parents=True, exist_ok=True)
        if not still and (out / "done.json").exists():
            print(f"[shot] {shot['index'] + 1}/{len(shots)} already rendered", flush=True)
            continue
        t_build = time.time()
        sc, frames = build_shot(job, shot)
        print(f"[shot] {shot['index'] + 1}/{len(shots)} built {shot.get('environment')} / "
              f"{', '.join(shot.get('props', [])) or '-'} / {shot.get('character')} "
              f"in {time.time() - t_build:.1f}s", flush=True)
        if still:
            f = max(1, min(frames, int(frames * 0.6)))
            sc.frame_set(f)
            K.apply((f - 1) / job["fps"])
            sc.render.filepath = str(out.parent / f"preview_{shot['index'] + 1:02d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[shot] preview {sc.render.filepath}", flush=True)
            continue
        _clean_partial_frames(out)
        sc.render.filepath = str(out) + "/"
        state = {"t": time.time(), "n": 0}

        def progress(scene, *_):
            state["n"] += 1
            if state["n"] % 10 == 0 or scene.frame_current == frames:
                per = (time.time() - state["t"]) / state["n"]
                print(f"[shot] {shot['index'] + 1}/{len(shots)} frame {scene.frame_current}/{frames} "
                      f"({per:.1f}s/frame)", flush=True)
        bpy.app.handlers.render_post.append(progress)
        bpy.ops.render.render(animation=True)
        bpy.app.handlers.render_post.remove(progress)
        missing = [i for i in range(1, frames + 1) if not (out / f"{i:04d}.png").exists()]
        if missing:
            raise RuntimeError(f"shot {shot['index'] + 1}: {len(missing)} frames missing after render")
        (out / "done.json").write_text(json.dumps({"frames": frames}), encoding="utf-8")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: blender -b -P shot.py -- job.json [--still]")
    job = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    try:
        render_job(job, still="--still" in argv)
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        raise


main()
