"""Environments: sky, ground, lighting and set dressing around a clear central stage.

Each builder keeps the stage (radius ~3 around the origin) and the corridor
towards the camera (-Y) free, so props and characters stay visible.
"""
import math

import bpy
from mathutils import Vector

import character
import kit as K
import props as P

TIMES = {
    "day": dict(zenith="#2f6fd6", horizon="#cfe6ff", elev=50, az=-35, sun="#fff2dc", energy=3.4,
                world=0.9, stars=0.0),
    "sunrise": dict(zenith="#4a5fa8", horizon="#ffc48a", elev=14, az=-55, sun="#ffb27a", energy=3.0,
                    world=0.95, stars=0.0),
    "sunset": dict(zenith="#3d2f6b", horizon="#ff9466", elev=12, az=140, sun="#ffa066", energy=3.0,
                   world=1.0, stars=0.0),
    "night": dict(zenith="#081030", horizon="#2a3d70", elev=40, az=-30, sun="#a9bcff", energy=1.1,
                  world=0.8, stars=1.0),
}


class Env:
    def __init__(self, name, time):
        self.name = name
        self.time = time
        self.water = None
        self.indoor = False
        self.floating = False
        self.ground = lambda x, y: 0.0
        self.sun_dir = Vector((0, 1, 1)).normalized()


# ------------------------------------------------------------ helpers ---


def _hills(flat=6.0, amp=2.5, seed=0.0, freq=0.06, rise=0.08):
    def h(x, y):
        r = math.hypot(x, y)
        k = K.smooth((r - flat) / (flat * 2.2))
        n = K.noise.noise(Vector((x * freq, y * freq, seed)))
        micro = 0.04 * K.noise.noise(Vector((x * 0.45, y * 0.45, seed + 3.3)))
        return k * amp * (0.55 + 0.6 * n) + k * k * max(0.0, r - flat) * rise + micro
    return h


def _terrain(env, c1, c2, size=75, res=90, **hills):
    env.ground = _hills(**hills)
    K.grid(size=size, res=res, height=env.ground, name="terrain",
           material=K.two_tone_material("ground", c1, c2, scale=0.08))


def scatter(rng, n, rmin, rmax, spacing=1.8, front=4.5):
    pts = []
    for _ in range(n * 40):
        if len(pts) >= n:
            break
        a = rng.uniform(0, K.TAU)
        r = rmin + (rmax - rmin) * math.sqrt(rng.random())
        x, y = r * math.cos(a), r * math.sin(a)
        if y < 3 and abs(x) < front + max(0.0, -y) * 0.8:
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < spacing ** 2 for px, py in pts):
            continue
        pts.append((x, y))
    return pts


def _place(built, env, x, y, scale=1.0, rot=None, rng=None):
    built.root.location = (x, y, env.ground(x, y))
    built.root.scale = (scale, scale, scale)
    built.root.rotation_euler.z = rot if rot is not None else (rng.uniform(0, K.TAU) if rng else 0)
    return built


def _sky_and_sun(env, T, c, ground=None):
    K.world_gradient(T["zenith"], T["horizon"], T["world"], stars=T["stars"], ground=ground)
    elev, az = math.radians(T["elev"]), math.radians(T["az"])
    sun = K.light("SUN", T["energy"], T["sun"], rot=(math.pi / 2 - elev, 0, az), size=math.radians(2.5))
    d = sun.matrix_world.to_3x3() @ Vector((0, 0, 1))
    env.sun_dir = d.normalized()
    # cool fill from the camera side so faces never go black
    K.light("SUN", T["energy"] * (0.18 if env.time == "day" else 0.32),
            "#cfe2ff" if env.time != "sunset" else "#ffd6c2",
            rot=(math.radians(60), 0, math.radians(20)), size=math.radians(10), shadow=False)
    wanted = set(getattr(c, "props", ()))
    if env.time in ("sunrise", "sunset") and env.sun_dir.y > 0 and "sun" not in wanted:
        s = P.sun(c)
        s.root.location = env.sun_dir * 90 + Vector((0, 0, -2))
        s.root.scale = (6, 6, 6)
    if env.time == "night" and not env.indoor and "moon" not in wanted:
        m = P.moon(c)
        m.root.location = (-14, 70, 26)
        m.root.scale = (3.5, 3.5, 3.5)


def _fog(T, start, end, amount):
    K.FOG.update(color=K.lin(T["horizon"]), start=start, end=end, amount=amount)


def palm(c, parent=None):
    root = K.empty("palm", parent=parent)
    lean = c.rng.uniform(0.15, 0.35)
    p = Vector((0, 0, 0))
    for i in range(6):
        nxt = p + Vector((lean * 0.25 * i * 0.3, 0, 0.5))
        K.segment(p, nxt, r=0.13 - i * 0.012, seg=7, parent=root, color="#9c6644" if i % 2 else "#7f5539")
        p = nxt
    top = K.empty("crown", parent=root, loc=p)
    for i in range(7):
        a = K.TAU * i / 7
        leaf = K.ico(0.5, sub=1, parent=top, scale=(1.6, 0.35, 0.08), color=c.rng.choice(["#2d6a4f", "#40916c"]),
                     loc=(0.7 * math.cos(a), 0.7 * math.sin(a), -0.15))
        leaf.rotation_euler = (0, 0.45, a)
    for i in range(3):
        K.sphere(0.09, seg=8, rings=6, parent=top, loc=(0.1 * math.cos(i * 2), 0.1 * math.sin(i * 2), -0.12),
                 color="#6f4518")
    K.sway(top, 0.04, 0.35, 0, c.rng.uniform(0, 6))
    return root


def cactus(c, parent=None):
    root = K.empty("cactus", parent=parent)
    g = "#588157"
    h = c.rng.uniform(1.2, 1.9)
    K.cyl(0.16, h, seg=8, base=True, parent=root, color=g)
    K.hemisphere(0.16, seg=8, rings=6, parent=root, loc=(0, 0, h), color=g)
    for side in (-1, 1):
        z = c.rng.uniform(0.5, h * 0.7)
        K.segment((0, 0, z), (side * 0.38, 0, z), r=0.1, seg=8, parent=root, color=g)
        K.cyl(0.1, 0.45, seg=8, base=True, parent=root, loc=(side * 0.38, 0, z), color=g)
    return root


def snowman(c, loc):
    root = K.empty("snowman", loc=loc)
    for z, r in ((0.38, 0.42), (0.98, 0.3), (1.42, 0.21)):
        K.sphere(r, seg=16, rings=10, parent=root, loc=(0, 0, z), color="#f8f9fa")
    K.cone(0.05, 0.3, seg=8, parent=root, loc=(0, -0.3, 1.42), rot=(math.pi / 2, 0, 0), color="#fb8500")
    for x in (-0.07, 0.07):
        K.sphere(0.03, seg=6, rings=4, parent=root, loc=(x, -0.19, 1.5), color="#111111")
    K.cyl(0.24, 0.05, seg=16, base=True, parent=root, loc=(0, 0, 1.58), color="#212529")
    K.cyl(0.15, 0.25, seg=16, base=True, parent=root, loc=(0, 0, 1.6), color="#212529")
    return root


def _snowfall(c, n=90):
    for i in range(n):
        x, y, z0 = c.rng.uniform(-7, 7), c.rng.uniform(-8, 8), c.rng.uniform(0, 8)
        f = K.ico(0.035, sub=1, color="#ffffff", kind="emit", emit=0.8, loc=(x, y, z0))
        sp, ph = c.rng.uniform(0.5, 0.9), c.rng.uniform(0, 6)

        def fall(t, s, z0=z0, sp=sp, ph=ph):
            s.loc.z = (z0 - t * sp) % 8.0
            s.loc.x += 0.25 * math.sin(t * 0.8 + ph)
        K.animate(f, fall)


# -------------------------------------------------------- environments ---


def village(env, T, c):
    _fog(T, 20, 110, 0.75)
    _sky_and_sun(env, T, c)
    _terrain(env, "#86c95a", "#62a83e", seed=c.seed % 50, amp=2.2)
    for x, y in scatter(c.rng, 16, 5, 32):
        b = P.pine_tree(c) if c.rng.random() < 0.25 else P.tree(c)
        _place(b, env, x, y, c.rng.uniform(0.9, 1.5), rng=c.rng)
    for x, y in scatter(c.rng, 4, 7, 18, spacing=4):
        _place(P.house(c), env, x, y, c.rng.uniform(0.9, 1.2), rot=c.rng.uniform(-0.5, 0.5))
    for x in (-3.0, 3.2):
        _place(P.flowers(c), env, x, 2.0, 1.0, rng=c.rng)
    if env.time != "night":
        cl = P.clouds(c)
        cl.root.location = (0, 40, 14)
        cl.root.scale = (2.2, 2.2, 2.2)
    # villagers: a farmer carrying a load along the path, an elder resting
    _extra(c, -2.5, 5.2, math.pi / 2, "carry", kind="man", outfit="farmer")
    _extra(c, 3.4, 3.8, -0.7, "sit", kind=c.rng.choice(["old_man", "old_woman"]), travel=False)


def forest(env, T, c):
    _fog(T, 8, 60, 0.85)
    _sky_and_sun(env, T, c)
    _terrain(env, "#4f7942", "#3b5f30", seed=c.seed % 50, amp=1.6)
    for x, y in scatter(c.rng, 45, 4, 34, spacing=1.6, front=3.8):
        b = P.pine_tree(c) if c.rng.random() < 0.5 else P.tree(c)
        _place(b, env, x, y, c.rng.uniform(1.1, 2.0), rng=c.rng)
    for x, y in scatter(c.rng, 4, 3, 8, spacing=2):
        _place(P.rocks(c), env, x, y, 0.7, rng=c.rng)


def city(env, T, c):
    _fog(T, 25, 140, 0.7)
    _sky_and_sun(env, T, c)
    K.grid(size=90, res=2, name="plaza", material=K.two_tone_material("plaza", "#9aa5b1", "#8a95a2", 0.3))
    road_y = 6.0
    K.box(180, 4.0, 0.04, base=True, loc=(0, road_y, 0), color="#343a40")
    for x in range(-80, 81, 4):
        K.box(1.6, 0.12, 0.05, base=True, loc=(x, road_y, 0), color="#f8f9fa")
    for x in (-9.0, 9.0):
        K.box(4.0, 120, 0.04, base=True, loc=(x, road_y + 60, 0), color="#343a40")
    rng = c.rng
    for gx in range(-42, 43, 6):
        for gy in range(10, 70, 6):
            if abs(gx - 9) < 4.5 or abs(gx + 9) < 4.5 or rng.random() < 0.15:
                continue
            h = rng.uniform(4, 9) + (gy - 10) * rng.uniform(0.1, 0.35)
            P.tower(c, None, (gx + rng.uniform(-0.6, 0.6), gy, 0), rng.uniform(3.2, 4.8), rng.uniform(3.2, 4.8), h)
    for x in range(-24, 25, 8):
        K.cyl(0.06, 3.2, seg=8, base=True, loc=(x, road_y - 2.4, 0), color="#495057", kind="metal")
        K.box(0.7, 0.18, 0.08, loc=(x + 0.3, road_y - 2.4, 3.2), color="#495057", kind="metal")
        K.box(0.4, 0.14, 0.04, loc=(x + 0.45, road_y - 2.4, 3.15), color="#fff3b0", kind="emit",
              emit=6 if env.time == "night" else 0.5)
        if env.time == "night":
            K.light("POINT", 120, "#ffd8a8", loc=(x + 0.45, road_y - 2.4, 3.0), size=0.3, shadow=False)
    for i, (y, d) in enumerate(((road_y - 0.9, 1), (road_y + 0.9, -1))):
        car = P.car(c)
        car.root.location = (d * 3.0 * (i + 1), y, 0)
        car.root.rotation_euler.z = 0 if d > 0 else math.pi
    for x in (-5.5, 5.5):
        K.box(1.2, 1.2, 0.5, base=True, loc=(x, 2.5, 0), color="#adb5bd")
        _place(P.tree(c), env, x, 2.5, 1.0, rng=c.rng).root.location.z = 0.5
    # people on the pavement
    for (x, y, facing, action) in ((-4.0, 3.7, math.pi / 2, "walk"), (3.0, 4.2, -math.pi / 2, "walk"),
                                   (6.5, 3.5, -math.pi / 2, "walk"), (-2.8, 3.2, 0.4, "phone")):
        _extra(c, x, y, facing, action, travel=action == "walk")


def space(env, T, c):
    env.floating = True
    T = dict(T, zenith="#05061a", horizon="#2b1650", world=0.45, stars=1.2)
    _fog(T, 0, 1, 0.0)
    K.world_gradient(T["zenith"], T["horizon"], T["world"], stars=T["stars"])
    sun = K.light("SUN", 3.2, "#fff4e6", rot=(math.radians(55), 0, math.radians(-40)), size=math.radians(1))
    env.sun_dir = (sun.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    K.light("SUN", 0.8, "#7aa2ff", rot=(math.radians(-60), 0, math.radians(20)), shadow=False)
    for (x, y, z, s, col) in ((-22, 70, 18, 5, "#e76f51"), (30, 90, -6, 9, "#4361ee"), (18, 45, 20, 2.2, "#ffd166")):
        K.sphere(1, seg=32, rings=16, loc=(x, y, z), scale=s, color=col, kind="gloss")
    for i in range(14):
        a = c.rng.uniform(0, K.TAU)
        r = c.rng.uniform(7, 22)
        x, y = r * math.cos(a), abs(r * math.sin(a)) + 3
        rock = K.ico(c.rng.uniform(0.2, 0.8), sub=1, jitter=0.3, rng=c.rng, loc=(x, y, c.rng.uniform(-3, 6)),
                     color=c.rng.choice(["#6c757d", "#5c5470", "#7d6e83"]))
        K.spin(rock, c.rng.uniform(-0.08, 0.08), c.rng.randrange(3))
        K.bob(rock, 0.2, 0.1, i)


def ocean(env, T, c):
    _fog(T, 25, 150, 0.8)
    _sky_and_sun(env, T, c)
    env.water = -0.32
    water = K.grid(size=110, res=130, name="sea", color="#1b6ca8" if env.time != "night" else "#0d2c54",
                   kind="water", loc=(0, 0, env.water))
    tex = bpy.data.textures.new("waves", "CLOUDS")
    tex.noise_scale = 2.2
    drv = K.empty("wave_driver")
    mod = water.modifiers.new("waves", "DISPLACE")
    mod.texture = tex
    mod.texture_coords = "OBJECT"
    mod.texture_coords_object = drv
    mod.strength = 0.45
    K.drift(drv, (0.35, 0.22, 0.05))
    rad, sq = 4.6, 0.26
    K.hemisphere(rad, seg=32, rings=16, loc=(0, 0, -1.15), scale=(1, 1, sq), color="#f2d492")
    env.ground = lambda x, y: -1.15 + sq * math.sqrt(max(0.0, rad * rad - x * x - y * y))
    for a in (0.7, 1.9, 2.6):
        x, y = 3.4 * math.cos(a), 3.4 * math.sin(a)
        p = palm(c)
        p.location = (x, y, env.ground(x, y) - 0.05)
        p.rotation_euler.z = a + math.pi
    for x, y in ((-2.8, -1.0), (3.0, 0.8)):
        _place(P.rocks(c), env, x, y, 0.5, rng=c.rng)
    for (x, y, s) in ((-40, 60, 6), (35, 80, 9), (70, 50, 4)):
        K.hemisphere(1, seg=16, rings=8, loc=(x, y, -1.2), scale=(s, s, s * 0.35), color="#52b788")


def desert(env, T, c):
    T = dict(T)
    if env.time == "day":
        T.update(horizon="#ffe8c2", zenith="#3f8fd8", energy=3.9)
    _fog(T, 25, 130, 0.7)
    _sky_and_sun(env, T, c)

    def dunes(x, y):
        r = math.hypot(x, y)
        k = K.smooth((r - 6) / 14)
        return k * (1.4 + 1.3 * math.sin(x * 0.11 + 2.0 * K.noise.noise(Vector((x * 0.03, y * 0.03, 1.0))))
                    + 0.8 * math.sin(y * 0.07)) + k * k * max(0.0, r - 6) * 0.06
    env.ground = dunes
    K.grid(size=75, res=90, height=dunes, name="dunes",
           material=K.two_tone_material("sand", "#edc988", "#d9a95f", scale=0.05))
    for x, y in scatter(c.rng, 7, 5, 22, spacing=3):
        cc = cactus(c)
        cc.location = (x, y, dunes(x, y) - 0.05)
    for x, y in scatter(c.rng, 4, 4, 14, spacing=3):
        _place(P.rocks(c), env, x, y, 0.8, rng=c.rng)


def mountains(env, T, c):
    _fog(T, 30, 160, 0.75)
    _sky_and_sun(env, T, c)
    _terrain(env, "#6a994e", "#8a9a7b", seed=c.seed % 50, amp=3.0)
    for (x, y, s) in ((0, 55, 2.4), (-38, 70, 2.0), (40, 65, 1.9)):
        m = P.mountain(c)
        m.root.location = (x, y, env.ground(x, y) - 1)
        m.root.scale = (s, s, s)
    for x, y in scatter(c.rng, 18, 5, 30):
        _place(P.pine_tree(c), env, x, y, c.rng.uniform(0.9, 1.6), rng=c.rng)
    for x, y in scatter(c.rng, 3, 4, 10, spacing=3):
        _place(P.rocks(c), env, x, y, 0.8, rng=c.rng)
    if env.time != "night":
        cl = P.clouds(c)
        cl.root.location = (0, 45, 16)
        cl.root.scale = (2.5, 2.5, 2.5)


def snow(env, T, c):
    T = dict(T)
    if env.time == "day":
        T.update(zenith="#8fb8e8", horizon="#eef4fb")
    _fog(T, 10, 80, 0.85)
    _sky_and_sun(env, T, c)
    _terrain(env, "#f8f9fa", "#e3eaf2", seed=c.seed % 50, amp=2.0)
    for x, y in scatter(c.rng, 22, 4.5, 30):
        _place(P.pine_tree(c, snowy=True), env, x, y, c.rng.uniform(0.9, 1.7), rng=c.rng)
    snowman(c, (-3.2, 2.6, env.ground(-3.2, 2.6)))
    _snowfall(c)


def room(env, T, c):
    env.indoor = True
    night = env.time == "night"
    _fog(T, 0, 1, 0.0)
    K.world_gradient("#d8d0c8", "#e8e0d8", 0.35 if night else 0.55)
    wall = c.rng.choice(["#f1e3d3", "#dbe7e4", "#f6e7cb", "#e3d5ca", "#d6e2e9"])
    K.box(18, 14, 0.2, loc=(0, 1, -0.1), material=K.two_tone_material("floor", "#c8a27a", "#b08968", 0.6))
    K.box(18, 0.3, 8, base=True, loc=(0, 4.6, 0), color=wall)
    K.box(0.3, 14, 8, base=True, loc=(-6.2, 1, 0), color=wall)
    K.box(18, 0.32, 0.35, base=True, loc=(0, 4.42, 0), color="#ffffff")
    # window
    wx, wz = 2.4, 3.0
    K.box(2.6, 0.12, 2.1, loc=(wx, 4.42, wz), color="#ffffff", kind="gloss")
    sky = "#0b1d3a" if night else "#9ad1ff"
    for dx in (-0.62, 0.62):
        for dz in (-0.47, 0.47):
            K.box(1.1, 0.05, 0.82, loc=(wx + dx, 4.36, wz + dz), color=sky, kind="emit", emit=0.6 if night else 3.0)
    K.light("AREA", 60 if night else 700, "#9fb4ff" if night else "#fff1d6", loc=(wx, 3.6, wz),
            target=(0, 0, 1), size=2.4)
    K.light("AREA", 160 if night else 260, "#ffe8cc", loc=(0, 0, 6.5), size=6, shadow=False)
    # table + lamp
    tx, ty = 3.3, 2.3
    K.box(1.7, 0.9, 0.08, loc=(tx, ty, 0.82), color="#8d5524", kind="gloss")
    for dx in (-0.75, 0.75):
        for dy in (-0.38, 0.38):
            K.box(0.07, 0.07, 0.8, base=True, loc=(tx + dx, ty + dy, 0), color="#6f4518")
    K.cyl(0.12, 0.05, seg=12, base=True, loc=(tx + 0.5, ty, 0.86), color="#343a40")
    K.cyl(0.02, 0.5, seg=6, base=True, loc=(tx + 0.5, ty, 0.9), color="#343a40")
    K.cyl(0.22, 0.28, r2=0.13, seg=16, base=True, loc=(tx + 0.5, ty, 1.3), color="#ffe8a3", kind="emit",
          emit=3.0 if night else 0.8)
    K.light("POINT", 120 if night else 20, "#ffcf8a", loc=(tx + 0.5, ty - 0.2, 1.35), size=0.2)
    # a family member on the sofa behind
    sofa = c.rng.choice(["#6d597a", "#457b9d", "#bc6c25", "#2a9d8f"])
    K.box(1.7, 0.75, 0.42, base=True, loc=(-2.0, 3.75, 0), color=sofa, bevel=0.05)
    K.box(1.7, 0.22, 0.85, base=True, loc=(-2.0, 4.15, 0), color=K.shade(sofa, 0.8), bevel=0.05)
    for dx in (-0.85, 0.85):
        K.box(0.2, 0.75, 0.62, base=True, loc=(-2.0 + dx, 3.75, 0), color=K.shade(sofa, 0.8), bevel=0.05)
    _extra(c, -2.25, 3.75, 0.2, c.rng.choice(["read", "phone", "drink"]),
           kind=c.rng.choice(["old_man", "old_woman", "woman", "man"]), seated=True, travel=False)
    # shelf with books
    K.box(1.8, 0.4, 0.06, loc=(-3.4, 4.3, 2.6), color="#6f4518")
    x = -4.15
    for i in range(9):
        w = c.rng.uniform(0.1, 0.16)
        h = c.rng.uniform(0.35, 0.5)
        K.box(w, 0.3, h, base=True, loc=(x, 4.25, 2.63), color=c.rng.choice(P_COLORS))
        x += w + 0.02
    # picture, rug, plant
    K.box(1.2, 0.06, 0.9, loc=(-1.0, 4.42, 3.3), color="#3d2b1f")
    K.box(1.0, 0.04, 0.7, loc=(-1.0, 4.38, 3.3), color=c.accent, kind="emit", emit=0.4)
    K.cyl(2.6, 0.02, seg=40, base=True, loc=(0, 0.6, 0), color=c.accent)
    K.cyl(0.3, 0.5, r2=0.24, seg=12, base=True, loc=(-4.6, 2.8, 0), color="#bc6c25")
    for i in range(5):
        a = K.TAU * i / 5
        leaf = K.ico(0.35, sub=1, loc=(-4.6 + 0.25 * math.cos(a), 2.8 + 0.25 * math.sin(a), 0.95),
                     scale=(0.6, 0.6, 1.4), color="#40916c")
        leaf.rotation_euler = (0.4 * math.sin(a), 0.4 * math.cos(a), 0)


P_COLORS = ["#e63946", "#457b9d", "#2a9d8f", "#f4a261", "#6d597a", "#ffb703"]


def studio(env, T, c):
    env.indoor = True
    looks = {
        "day": ("#e7f0ff", "#cddcff", ["#ffafcc", "#a2d2ff", "#bde0fe", "#cdb4db", "#ffc8dd"], ("#ffffff", "#a2d2ff", "#ffafcc")),
        "sunrise": ("#ffe5d9", "#ffcdb2", ["#ffb4a2", "#e5989b", "#ffd6a5", "#b5838d"], ("#fff1e6", "#ffb4a2", "#ffd166")),
        "sunset": ("#ffd6c2", "#f4978e", ["#f08080", "#f8ad9d", "#fbc4ab", "#9d4edd"], ("#ffe5d9", "#ff7b54", "#9d4edd")),
        "night": ("#1b1f3b", "#11142b", ["#4cc9f0", "#f72585", "#7209b7", "#4361ee"], ("#c8d1ff", "#4cc9f0", "#f72585")),
    }
    bg, bg2, shapes, (key, rim1, rim2) = looks[env.time]
    _fog(T, 0, 1, 0.0)
    K.world_gradient(bg, bg2, 0.5)
    prof = [(-25.0, 0.0), (6.0, 0.0)]
    for i in range(1, 9):
        a = (math.pi / 2) * i / 8
        prof.append((6.0 + 5.0 * math.sin(a), 5.0 - 5.0 * math.cos(a)))
    prof.append((11.0, 30.0))
    import bmesh
    bm = bmesh.new()
    xs = [-40 + i * 4 for i in range(21)]
    rows = [[bm.verts.new((x, y, z)) for (y, z) in prof] for x in xs]
    for i in range(len(xs) - 1):
        for j in range(len(prof) - 1):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    K.mesh_object("cyclorama", bm, color=bg, smooth=True)
    for i in range(8):
        kind = i % 4
        x = c.rng.choice((-1, 1)) * c.rng.uniform(2.8, 6.5)
        loc = (x, c.rng.uniform(4.5, 9), c.rng.uniform(1.0, 6.0))
        col = shapes[i % len(shapes)]
        s = c.rng.uniform(0.35, 0.8)
        if kind == 0:
            ob = K.sphere(s, seg=24, rings=12, loc=loc, color=col, kind="gloss")
        elif kind == 1:
            ob = K.torus(s, s * 0.35, seg=32, rseg=12, loc=loc, color=col, kind="gloss")
        elif kind == 2:
            ob = K.box(s * 1.3, s * 1.3, s * 1.3, loc=loc, color=col, kind="gloss", bevel=0.08)
        else:
            ob = K.cone(s, s * 1.6, seg=24, loc=loc, color=col, kind="gloss", smooth=True)
        K.bob(ob, 0.25, c.rng.uniform(0.1, 0.25), i)
        K.spin(ob, c.rng.uniform(-0.06, 0.06), c.rng.randrange(3))
    K.light("AREA", 650, key, loc=(-4, -5, 6), target=(0, 0, 1), size=5)
    K.light("AREA", 500, rim1, loc=(-4.5, 4, 4.5), target=(0, 0, 1), size=3, shadow=False)
    K.light("AREA", 500, rim2, loc=(4.5, 4, 4.5), target=(0, 0, 1), size=3, shadow=False)
    env.sun_dir = Vector((0, 1, 1)).normalized()


# ------------------------------------------------- everyday / business places ---
# The camera looks along +Y and a vertical frame is narrow: set dressing that matters sits
# behind the stage (|x| < ~3.5, y 2..6); the sides only show in orbit shots and landscape videos.

FACADES = ["#f4a261", "#e9c46a", "#a8dadc", "#ffcad4", "#cdb4db", "#f1faee", "#b7e4c7", "#ffd6a5"]
CARDBOARD = ["#c8a165", "#d4a373", "#bc8a5f", "#cfa46a"]


def _checker_material(name, c1, c2, scale=1.5, rough=0.45):
    def build(nt, bsdf):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        ch = nt.nodes.new("ShaderNodeTexChecker")
        ch.inputs["Scale"].default_value = scale
        ch.inputs["Color1"].default_value = (*K.lin(c1), 1)
        ch.inputs["Color2"].default_value = (*K.lin(c2), 1)
        nt.links.new(tc.outputs["Object"], ch.inputs["Vector"])
        nt.links.new(ch.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = rough
    return K.custom_material(name, build)


def _interior(env, T, floor_mat, wall, back=4.6, height=8.0, world=("#e8e2d8", "#f5efe6", 0.45)):
    env.indoor = True
    _fog(T, 0, 1, 0.0)
    K.world_gradient(*world)
    K.box(18, 14, 0.2, loc=(0, 1, -0.1), material=floor_mat)
    K.box(18, 0.3, height, base=True, loc=(0, back + 0.15, 0), color=wall)
    K.box(18, 0.32, 0.22, base=True, loc=(0, back - 0.01, 0), color="#ffffff")
    K.box(0.3, 14, height, base=True, loc=(-6.2, 1, 0), color=wall)
    K.box(0.3, 14, height, base=True, loc=(6.2, 1, 0), color=wall)


def _extra(c, x, y, facing, action, kind=None, outfit="casual", scale=1.0, seated=False, mode=None,
           travel=True, hand=0):
    """A background person (shopper, tea drinker, colleague...)."""
    kind = kind or c.rng.choice(["man", "woman", "man", "woman", "old_man", "boy", "girl"])
    look = character.random_look(c.rng, kind)
    ch = character.build(look, c, loc=(x, y, 0), scale=scale, outfit=outfit)
    character.act(ch, action, c, phase=c.rng.uniform(0, 3), facing=facing, travel=travel, seated=seated,
                  mode=mode, hand=hand)
    return ch


def _plant(c, x, y, s=1.0):
    K.cyl(0.25 * s, 0.5 * s, r2=0.2 * s, seg=12, base=True, loc=(x, y, 0), color="#e9ecef", kind="gloss")
    for i in range(6):
        a = K.TAU * i / 6 + c.rng.uniform(0, 0.5)
        leaf = K.ico(0.3 * s, sub=1, loc=(x + 0.18 * s * math.cos(a), y + 0.18 * s * math.sin(a), 0.9 * s),
                     scale=(0.5, 0.5, 1.5), color=c.rng.choice(["#40916c", "#52b788", "#2d6a4f"]))
        leaf.rotation_euler = (0.45 * math.sin(a), 0.45 * math.cos(a), 0)
        K.sway(leaf, 0.04, 0.3, 0, i)


def _lamp(x, y, z, night, top=8.0, color="#212529"):
    K.cyl(0.01, top - z, seg=4, base=True, loc=(x, y, z + 0.25), color=color)
    K.cone(0.3, 0.28, seg=20, loc=(x, y, z + 0.12), color=color, kind="gloss")
    K.sphere(0.09, seg=10, rings=6, loc=(x, y, z - 0.02), color="#fff3c4", kind="emit", emit=8)
    K.light("POINT", 120 if night else 50, "#ffd8a8", loc=(x, y, z - 0.18), size=0.2, shadow=False)


def _shelf_unit(c, x, y, w=2.8, h=2.5, levels=(0.25, 0.85, 1.45, 2.05), wood="#8d6e63"):
    """Shelves against a back wall, full of products facing the camera."""
    d = 0.5
    K.box(w, 0.04, h, base=True, loc=(x, y + d / 2, 0), color=K.shade(wood, 0.75))
    for sx in (-1, 1):
        K.box(0.05, d, h, base=True, loc=(x + sx * w / 2, y, 0), color=wood)
    for z in levels:
        K.box(w, d, 0.04, base=True, loc=(x, y, z - 0.04), color=wood)
        px = x - w / 2 + 0.08
        while px < x + w / 2 - 0.2:
            col = c.rng.choice(P.PRODUCT_COLS)
            r = c.rng.random()
            if r < 0.5:
                bw, bh = c.rng.uniform(0.12, 0.22), c.rng.uniform(0.2, 0.38)
                K.box(bw, 0.26, bh, base=True, loc=(px + bw / 2, y - 0.05, z), color=col, kind="gloss")
                if c.rng.random() < 0.6:
                    K.box(bw + 0.004, 0.262, bh * 0.25, base=True, loc=(px + bw / 2, y - 0.05, z + bh * 0.4),
                          color="#ffffff")
                px += bw + 0.025
            elif r < 0.8:
                rad, bh = c.rng.uniform(0.045, 0.065), c.rng.uniform(0.22, 0.32)
                K.cyl(rad, bh, seg=10, base=True, loc=(px + rad, y - 0.08, z), color=col, kind="gloss")
                K.cyl(rad * 0.4, 0.07, seg=8, base=True, loc=(px + rad, y - 0.08, z + bh), color="#f8f9fa")
                px += 2 * rad + 0.03
            else:
                rad = c.rng.uniform(0.07, 0.09)
                K.cyl(rad, 0.17, seg=12, base=True, loc=(px + rad, y - 0.08, z), color=col, kind="gloss")
                K.cyl(rad * 1.05, 0.04, seg=12, base=True, loc=(px + rad, y - 0.08, z + 0.17), color="#343a40",
                      kind="metal")
                px += 2 * rad + 0.03


def shop(env, T, c):
    night = env.time == "night"
    wall = c.rng.choice(["#fdf0d5", "#e9f5db", "#f1e3d3", "#dbe7e4"])
    _interior(env, T, _checker_material("shop_floor", "#e9ecef", "#c9cfd6", 1.4), wall)
    for ux in (-1.45, 1.45):
        _shelf_unit(c, ux, 4.15)
    # shop banner over the shelves
    K.box(7.0, 0.06, 0.55, loc=(0, 4.38, 3.0), color=c.accent, kind="emit", emit=0.9)
    for i in range(7):
        K.cyl(0.11, 0.02, seg=16, loc=(-3.0 + i, 4.34, 3.0), rot=(math.pi / 2, 0, 0), color="#ffffff",
              kind="emit", emit=1.2)
    # drinks fridge (left)
    fx, fy = -3.75, 3.85
    K.box(1.1, 0.75, 2.1, base=True, loc=(fx, fy, 0), color="#f8f9fa", kind="gloss", bevel=0.03)
    K.box(0.95, 0.02, 1.7, loc=(fx, fy - 0.36, 1.0), color="#bde0fe", kind="emit", emit=0.6)
    for zz in (0.35, 0.85, 1.35):
        K.box(0.95, 0.3, 0.02, loc=(fx, fy - 0.2, zz - 0.02), color="#ced4da")
        for k in range(6):
            K.cyl(0.045, 0.26, seg=10, base=True, loc=(fx - 0.38 + k * 0.15, fy - 0.28, zz),
                  color=c.rng.choice(("#e63946", "#ff9f1c", "#06d6a0", "#3a86ff", "#212529")), kind="gloss")
    K.box(0.97, 0.02, 1.72, loc=(fx, fy - 0.4, 1.0), color="#caf0f8", kind="glass")
    K.box(1.1, 0.05, 0.22, loc=(fx, fy - 0.39, 1.98), color=c.accent, kind="emit", emit=1.5)
    # counter with a cash register (right)
    cx, cy = 3.0, 2.55
    K.box(2.0, 0.8, 1.0, base=True, loc=(cx, cy, 0), color="#8d5524", kind="gloss", bevel=0.02)
    K.box(2.06, 0.86, 0.05, base=True, loc=(cx, cy, 1.0), color="#212529", kind="gloss")
    K.box(1.9, 0.02, 0.5, loc=(cx, cy - 0.41, 0.55), color=c.accent)
    K.box(0.45, 0.4, 0.18, base=True, loc=(cx - 0.45, cy + 0.05, 1.05), color="#495057", kind="gloss",
          bevel=0.02)
    K.box(0.32, 0.03, 0.2, loc=(cx - 0.45, cy - 0.06, 1.38), rot=(0.3, 0, 0), color="#4cc9f0", kind="emit",
          emit=2)
    K.cyl(0.14, 0.32, seg=16, base=True, loc=(cx + 0.35, cy, 1.05), color="#e9f5ff", kind="glass")
    for k in range(10):
        K.sphere(0.04, seg=8, rings=5, loc=(cx + 0.35 + c.rng.uniform(-0.08, 0.08), cy + c.rng.uniform(-0.08, 0.08),
                                            1.1 + 0.03 * k), color=c.rng.choice(P.PRODUCT_COLS), kind="gloss")
    for x in (-2.2, 0.0, 2.2):
        _lamp(x, 1.8, 3.6, night)
    K.light("AREA", 420, "#fff4e6", loc=(0, 0.5, 6.0), size=7)
    K.box(3.0, 1.8, 0.01, base=True, loc=(0, 0.4, 0), color=K.shade(c.accent, 0.55))
    # people: a cashier behind the counter, shoppers looking at the shelves
    _extra(c, cx + 0.3, cy + 0.65, 0.15, "idle", outfit="shopkeeper", travel=False)
    _extra(c, -2.3, 3.25, math.pi + 0.55, "think", travel=False)
    _extra(c, -0.9, 3.45, math.pi - 0.35, "idle", travel=False)


AWNINGS = [("#e63946", "#f1faee"), ("#2a9d8f", "#e9c46a"), ("#457b9d", "#f1faee"), ("#f4a261", "#fefae0"),
           ("#6a4c93", "#ffca3a"), ("#06d6a0", "#fefae0")]
GOODS = ["#fb8500", "#e63946", "#80b918", "#ffd60a", "#6a4c93", "#d00000", "#90be6d"]


def _stall(c, x, y, side, night, detail=True):
    """Market stall on the left (side=-1) or right (side=1) of the street, open towards the street."""
    root = K.empty("stall", loc=(x, y, 0))
    a, b = c.rng.choice(AWNINGS)
    tw, td = 2.4, 1.0
    K.box(td, tw, 0.75, base=True, parent=root, color="#8d5524")
    K.box(td + 0.08, tw + 0.08, 0.05, base=True, parent=root, loc=(0, 0, 0.75), color="#6f4518")
    for dx in (-td / 2, td / 2):
        for dy in (-tw / 2, tw / 2):
            K.cyl(0.035, 2.5, seg=6, base=True, parent=root, loc=(dx, dy, 0), color="#6f4518")
    n = 6
    for i in range(n):
        yy = -tw / 2 + tw * (i + 0.5) / n
        K.box(1.6, tw / n + 0.002, 0.03, parent=root, loc=(-side * 0.25, yy, 2.45), rot=(0, -side * 0.32, 0),
              color=a if i % 2 else b)
    K.box(0.03, tw, 0.18, parent=root, loc=(-side * 1.02, 0, 2.12), color=a)
    for k in range(3):
        yy = -0.8 + 0.8 * k
        col = c.rng.choice(GOODS)
        K.sphere(0.36, seg=12, rings=6, parent=root, loc=(-side * 0.05, yy, 0.8), scale=(1, 1, 0.5), color=col)
        if detail:
            for _ in range(7):
                K.sphere(0.08, seg=8, rings=5, parent=root,
                         loc=(-side * 0.05 + c.rng.uniform(-0.22, 0.22), yy + c.rng.uniform(-0.22, 0.22),
                              0.92 + c.rng.uniform(0, 0.06)), color=col, kind="gloss")
    K.sphere(0.06, seg=8, rings=5, parent=root, loc=(-side * 0.6, 0, 2.15), color="#fff3c4", kind="emit",
             emit=8 if night else 2)
    if night and detail:
        K.light("POINT", 60, "#ffd8a8", loc=(x - side * 0.6, y, 2.0), size=0.2, shadow=False)
    return root


def _street_buildings(c, xs, y0, y1, step=5.0, front=False):
    """Low colourful buildings; windows face the street (x = 0) or, with front=True, the camera."""
    win = dict(color="#ffd27a", kind="emit", emit=2) if c.night else dict(color="#22344f", kind="gloss")
    y = y0
    while y < y1:
        for x in xs:
            h = c.rng.uniform(3.5, 7.5)
            w = c.rng.uniform(3.6, 4.6)
            K.box(4.2, w, h, base=True, loc=(x, y, 0), color=c.rng.choice(FACADES))
            K.box(4.3, w + 0.1, 0.2, base=True, loc=(x, y, h), color="#6c757d")
            for z in [1.6 + 1.5 * k for k in range(int((h - 1) / 1.5))]:
                if front:
                    for dx in (-1.1, 0.0, 1.1):
                        K.box(0.6, 0.04, 0.7, loc=(x + dx, y - w / 2 - 0.01, z), **win)
                else:
                    K.box(0.04, 0.6, 0.7, loc=(x - math.copysign(2.12, x), y, z), **win)
        y += step


def market(env, T, c):
    night = env.time == "night"
    _fog(T, 25, 120, 0.55)
    _sky_and_sun(env, T, c)
    K.grid(size=80, res=2, name="street", material=K.two_tone_material("street", "#b8a48c", "#a8937a", 0.25))
    K.box(4.4, 90, 0.01, base=True, loc=(0, 40, 0), color="#9a8670")
    for side in (-1, 1):
        for y in range(2, 38, 3):
            _stall(c, side * 3.5, y + (0.0 if side < 0 else 1.4), side, night, detail=y < 14)
    _street_buildings(c, (-7.6, 7.6), -2, 44)
    for x in range(-14, 15, 5):
        h = c.rng.uniform(5, 9)
        K.box(4.8, 4, h, base=True, loc=(x, 46, 0), color=c.rng.choice(FACADES))
    for y in (5.0, 11.0, 17.0, 23.0):
        prev = None
        for i in range(13):
            u = i / 12
            p = Vector((-3.0 + 6.0 * u, y, 3.4 - 0.45 * math.sin(math.pi * u)))
            f = K.prism([(-0.13, 0), (0.13, 0), (0, -0.28)], depth=0.01, loc=p,
                        color=c.rng.choice(["#e63946", "#ffd60a", "#06d6a0", "#3a86ff", "#ff006e", "#ffffff"]))
            K.sway(f, 0.15, 0.7, 0, c.rng.uniform(0, 6))
            if prev is not None:
                K.segment(prev, p, r=0.006, color="#495057")
            prev = p
    for (x, y, facing) in ((-1.9, 9.0, 0.0), (1.8, 12.0, math.pi), (-1.3, 16.0, math.pi), (2.2, 7.5, 0.15),
                           (0.6, 20.0, 0.0)):
        _extra(c, x, y, facing, "walk")
    _extra(c, -4.3, 2.2, math.pi / 2 - 0.5, "talk", outfit="shopkeeper", travel=False)
    _extra(c, 4.3, 3.6, -math.pi / 2 + 0.5, "give", outfit="shopkeeper", travel=False)


def office(env, T, c):
    night = env.time == "night"
    env.indoor = True
    _fog(T, 0, 1, 0.0)
    K.world_gradient(T["zenith"], T["horizon"], 0.9 if not night else 0.7, stars=T["stars"] * 0.4)
    K.box(18, 14, 0.2, loc=(0, 1, -0.1), material=K.two_tone_material("office_floor", "#cbbba0", "#bba98c", 0.6))
    gy = 5.0
    K.box(18, 0.3, 4.2, base=True, loc=(0, gy + 0.2, 3.6), color="#e9ecef")
    K.box(18, 0.3, 0.3, base=True, loc=(0, gy, 0), color="#adb5bd")
    for x in range(-8, 9, 2):  # window frames (no glass pane: it reflects the sky and looks milky)
        K.box(0.1, 0.14, 3.6, base=True, loc=(x, gy, 0), color="#343a40", kind="metal")
    K.box(18, 0.14, 0.08, base=True, loc=(0, gy, 1.9), color="#343a40", kind="metal")
    for x in (-6.2, 6.2):
        K.box(0.3, 14, 8, base=True, loc=(x, 1, 0), color="#e9ecef")
    elev, az = math.radians(T["elev"]), math.radians(T["az"])
    sun = K.light("SUN", T["energy"] * 0.7, T["sun"], rot=(math.pi / 2 - elev, 0, az), size=math.radians(3))
    env.sun_dir = (sun.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    # the city far below
    K.grid(size=150, res=2, loc=(0, 0, -24), color="#6c757d")
    for _ in range(20):  # far enough away that sky shows between the towers
        x, y = c.rng.uniform(-55, 55), c.rng.uniform(20, 95)
        w = c.rng.uniform(5, 8)
        P.tower(c, None, (x, y, -24), w, w * c.rng.uniform(0.8, 1.2), c.rng.uniform(22, 34) + y * 0.1)
    # desks: a monitor facing the camera (left), a colleague at a laptop (right)
    for (x, y, sitter) in ((-2.5, 3.5, False), (2.5, 3.4, True)):
        K.box(1.7, 0.8, 0.05, base=True, loc=(x, y, 0.72), color="#f8f9fa", kind="gloss")
        for dx in (-0.78, 0.78):
            K.box(0.05, 0.7, 0.72, base=True, loc=(x + dx, y, 0), color="#adb5bd", kind="metal")
        if not sitter:
            K.box(0.25, 0.16, 0.02, base=True, loc=(x, y + 0.15, 0.77), color="#343a40")
            K.box(0.05, 0.05, 0.25, base=True, loc=(x, y + 0.18, 0.77), color="#343a40")
            K.box(0.8, 0.04, 0.48, base=True, loc=(x, y + 0.16, 0.95), color="#212529", kind="gloss")
            K.box(0.74, 0.01, 0.42, base=True, loc=(x, y + 0.135, 0.98), color="#1d3557", kind="emit", emit=1.5)
            for k, hgt in enumerate((0.1, 0.18, 0.14, 0.26, 0.3)):
                K.box(0.08, 0.008, hgt, base=True, loc=(x - 0.22 + k * 0.11, y + 0.128, 1.02),
                      color=("#4cc9f0", "#06d6a0", "#ffd166", "#f72585", "#4cc9f0")[k], kind="emit", emit=3)
            K.box(0.5, 0.16, 0.02, base=True, loc=(x, y - 0.15, 0.77), color="#dee2e6")
            K.cyl(0.05, 0.1, seg=12, base=True, loc=(x + 0.55, y - 0.1, 0.77), color=c.accent, kind="gloss")
        else:
            lap = P.laptop(c)
            lap.root.location = (x, y - 0.05, 0.77)
            lap.root.rotation_euler.z = math.pi
            lap.root.scale = (0.5, 0.5, 0.5)
            _extra(c, x, y + 0.75, 0.0, "work", outfit="office", seated=True, mode="type", travel=False)
            K.box(0.5, 0.45, 0.06, base=True, loc=(x, y + 0.78, 0.4), color="#212529")
        K.box(0.3, 0.22, 0.04, base=True, loc=(x - 0.5, y - 0.1, 0.77), color="#ffffff")
    for x in (-3.9, 3.9):
        _plant(c, x, 4.4, 1.2)
    K.light("AREA", 380 if not night else 300, "#fff6ea", loc=(0, 0.5, 6), size=8)


def _tea_stall(c, x, y, night):
    root = K.empty("tea_stall", loc=(x, y, 0))
    wood, dark = "#a0522d", "#6f4518"
    paint = c.rng.choice(["#2a9d8f", "#457b9d", "#e76f51", "#3a86ff"])
    W, D = 2.8, 1.4
    p = dict(parent=root)
    K.box(W, D, 0.08, base=True, color=dark, **p)
    K.box(W, 0.06, 2.6, base=True, loc=(0, D / 2, 0), color=paint, **p)
    for sx in (-1, 1):
        K.box(0.06, D, 2.6, base=True, loc=(sx * W / 2, 0, 0), color=paint, **p)
    K.box(W, 0.5, 1.0, base=True, loc=(0, -D / 2 + 0.25, 0), color=wood, bevel=0.02, **p)
    K.box(W + 0.1, 0.6, 0.05, base=True, loc=(0, -D / 2 + 0.25, 1.0), color=dark, **p)
    K.box(W + 0.6, D + 1.0, 0.05, loc=(0, -0.3, 2.72), rot=(0.12, 0, 0), color="#adb5bd", kind="metal", **p)
    K.box(W * 0.8, 0.06, 0.38, loc=(0, -1.32, 2.86), color=c.accent, kind="emit", emit=2.5 if night else 0.7, **p)
    for z in (1.55, 2.05):  # shelves with tins on the back wall
        K.box(W - 0.3, 0.3, 0.03, base=True, loc=(0, D / 2 - 0.18, z), color=dark, **p)
        for k in range(9):
            K.cyl(0.06, 0.18, seg=10, base=True, loc=(-1.1 + 0.27 * k, D / 2 - 0.18, z + 0.03),
                  color=c.rng.choice(P.PRODUCT_COLS), kind="gloss", **p)
    top = 1.05
    sx_, sy_ = -0.75, -D / 2 + 0.25
    K.cyl(0.22, 0.25, r2=0.25, seg=16, base=True, loc=(sx_, sy_, top), color="#9c6644", **p)
    K.cyl(0.18, 0.02, seg=16, base=True, loc=(sx_, sy_, top + 0.25), color="#ff6d00", kind="emit", emit=4, **p)
    K.sphere(0.2, seg=16, rings=10, loc=(sx_, sy_, top + 0.42), scale=(1, 1, 0.8), color="#ced4da",
             kind="metal", **p)
    K.sphere(0.04, seg=8, rings=5, loc=(sx_, sy_, top + 0.58), color="#343a40", **p)
    K.segment((sx_ + 0.15, sy_, top + 0.42), (sx_ + 0.34, sy_ - 0.05, top + 0.56), r=0.025, color="#ced4da",
              kind="metal", **p)
    K.torus(0.12, 0.012, seg=16, rseg=4, arc=0.5, loc=(sx_, sy_, top + 0.55), rot=(math.pi / 2, 0, 0),
            color="#343a40", **p)
    for i in range(6):  # steam from the spout
        puff = K.ico(0.06, sub=1, color="#ffffff", **p)
        base = Vector((sx_ + 0.36, sy_ - 0.05, top + 0.58))

        def steam(t, s, ph=i / 6, base=base):
            u = (t * 0.35 + ph) % 1.0
            s.loc = base + Vector((0.15 * math.sin(u * 5), 0, u * 1.0))
            s.scale *= max(1e-4, (0.5 + 2.0 * u) * (1 - u ** 2))
        K.animate(puff, steam)
    for k in range(4):  # glass jars of biscuits
        jx = 0.05 + 0.32 * k
        K.cyl(0.12, 0.3, seg=14, base=True, loc=(jx, sy_ - 0.05, top), color="#e9f5ff", kind="glass", **p)
        K.cyl(0.1, 0.2, seg=12, base=True, loc=(jx, sy_ - 0.05, top), color=c.rng.choice(("#d4a373", "#e9c46a",
                                                                                          "#bc6c25", "#f4a261")), **p)
        K.cyl(0.125, 0.05, seg=14, base=True, loc=(jx, sy_ - 0.05, top + 0.3),
              color=c.rng.choice(("#e63946", "#2a9d8f", "#ffd60a")), kind="gloss", **p)
    K.box(0.5, 0.3, 0.02, base=True, loc=(-0.2, sy_ - 0.05, top), color="#adb5bd", kind="metal", **p)
    for k in range(5):
        K.cyl(0.04, 0.07, seg=10, base=True, loc=(-0.38 + 0.09 * k, sy_ - 0.05, top + 0.02), color="#f8f9fa", **p)
    bunch = K.empty("bananas", loc=(1.0, -D / 2 + 0.05, 2.25), **p)
    K.cyl(0.02, 0.4, seg=6, base=True, parent=bunch, color="#6f4518")
    for k in range(9):
        a = K.TAU * k / 9
        bn = K.sphere(0.05, seg=8, rings=5, parent=bunch, loc=(0.09 * math.cos(a), 0.09 * math.sin(a), -0.05 * (k % 3)),
                      scale=(1, 1, 2.6), color="#ffd60a")
        bn.rotation_euler = (0.35 * math.sin(a), -0.35 * math.cos(a), 0)
    K.sway(bunch, 0.06, 0.4, 0)
    for k in range(6):  # snack packets on a string
        pk = K.box(0.12, 0.03, 0.18, loc=(-0.5 + 0.18 * k, -D / 2 + 0.02, 2.2),
                   color=c.rng.choice(P.PRODUCT_COLS), kind="gloss", **p)
        K.sway(pk, 0.08, 0.5, 1, k)
    K.segment((-0.65, -D / 2 + 0.02, 2.32), (0.5, -D / 2 + 0.02, 2.32), r=0.005, color="#495057", **p)
    K.sphere(0.07, seg=8, rings=5, loc=(-0.2, -0.2, 2.45), color="#fff3c4", kind="emit", emit=8 if night else 2, **p)
    if night:
        K.light("POINT", 150, "#ffd8a8", loc=(x - 0.2, y - 0.4, 2.3), size=0.2)
    return root


def _bench(x, y, rot, color="#8d5524"):
    b = K.empty("bench", loc=(x, y, 0), rot=(0, 0, rot))
    K.box(1.7, 0.36, 0.06, base=True, parent=b, loc=(0, 0, 0.42), color=color)
    for dx in (-0.7, 0.7):
        K.box(0.06, 0.3, 0.42, base=True, parent=b, color=K.shade(color, 0.7), loc=(dx, 0, 0))
    return b


def cafe(env, T, c):
    night = env.time == "night"
    _fog(T, 22, 110, 0.6)
    _sky_and_sun(env, T, c)
    K.grid(size=80, res=2, name="ground", material=K.two_tone_material("dust", "#c9b48a", "#b8a275", 0.2))
    K.box(160, 5.0, 0.03, base=True, loc=(0, 10.5, 0), color="#495057")
    for x in range(-60, 61, 5):
        K.box(2.0, 0.12, 0.04, base=True, loc=(x, 10.5, 0), color="#f8f9fa")
    _tea_stall(c, 0.0, 3.8, night)
    for (bx, by, rot) in ((-2.3, 1.6, 0.35), (2.4, 1.7, -0.35)):
        _bench(bx, by, rot)
    _extra(c, 0.35, 4.1, 0.0, "idle", kind="man", outfit="shopkeeper", travel=False)
    _extra(c, -2.3, 1.75, 0.35 + 0.6, "drink", seated=True, travel=False)
    _extra(c, 2.4, 1.85, -0.35 - 0.6, "talk", seated=True, travel=False, hand=1)
    _street_buildings(c, list(range(-26, 27, 6)), 17, 18, front=True)
    for x in (-5.5, 5.5, 16.5):
        K.cyl(0.08, 7.0, seg=8, base=True, loc=(x, 7.6, 0), color="#6c757d")
        K.box(1.4, 0.08, 0.08, loc=(x, 7.6, 6.6), color="#6c757d")
    for dz in (6.6, 6.3):
        for (x1, x2) in ((-16.5, -5.5), (-5.5, 5.5), (5.5, 16.5)):
            prev = None
            for i in range(9):
                u = i / 8
                pt = Vector((x1 + (x2 - x1) * u, 7.6, dz - 0.6 * math.sin(math.pi * u)))
                if prev is not None:
                    K.segment(prev, pt, r=0.012, color="#212529")
                prev = pt
    for (tx, ty) in ((-6.0, 6.0), (6.5, 5.5), (-10.0, 14.0), (11.0, 13.0)):
        _place(P.tree(c), env, tx, ty, c.rng.uniform(1.3, 1.8), rng=c.rng)
    if "rickshaw" not in getattr(c, "props", ()):
        r = P.rickshaw(c)
        r.root.location = (-1.0, 10.0, 0)


def classroom(env, T, c):
    night = env.time == "night"
    wall = c.rng.choice(["#e9f5db", "#fdf0d5", "#dbe7e4", "#f1e3d3"])
    _interior(env, T, K.two_tone_material("wood_floor", "#c8a27a", "#b08968", 0.6), wall)
    bx, bz = -0.5, 2.15
    K.box(4.6, 0.1, 2.0, loc=(bx, 4.42, bz), color="#6f4518")
    K.box(4.4, 0.06, 1.8, loc=(bx, 4.38, bz), color="#2d4a3e")
    K.box(4.4, 0.2, 0.05, base=True, loc=(bx, 4.28, bz - 1.02), color="#6f4518")
    chalk = dict(color="#f1f3f5", kind="emit", emit=0.5)
    K.torus(0.36, 0.014, seg=32, rseg=4, loc=(bx - 1.4, 4.34, bz + 0.2), rot=(math.pi / 2, 0, 0), **chalk)
    for a in (0.4, 2.3, 4.0):
        K.segment((bx - 1.4, 4.34, bz + 0.2), (bx - 1.4 + 0.36 * math.cos(a), 4.34, bz + 0.2 + 0.36 * math.sin(a)),
                  r=0.012, **chalk)
    K.segment((bx - 0.9, 4.34, bz + 0.2), (bx - 0.5, 4.34, bz + 0.2), r=0.014, **chalk)
    K.cone(0.05, 0.12, seg=6, loc=(bx - 0.45, 4.34, bz + 0.2), rot=(0, math.pi / 2, 0), **chalk)
    K.box(1.4, 0.01, 0.035, loc=(bx + 0.5, 4.34, bz + 0.68), color="#ffd166", kind="emit", emit=0.6)
    for row in range(5):
        x = bx - 0.25
        while x < bx + 1.9:
            w = c.rng.uniform(0.12, 0.35)
            line = K.box(w, 0.01, 0.03, loc=(x + w / 2, 4.34, bz + 0.42 - row * 0.22), **chalk)
            d0 = c.t0 + 0.2 * row + (x - bx) * 0.3

            def write(t, s, d0=d0):
                s.scale.x *= max(1e-4, K.clamp((t - d0) / 0.25))
            K.animate(line, write)
            x += w + 0.06
    # teacher's desk with books, a globe and an apple
    tx, ty = 2.7, 3.2
    K.box(1.6, 0.75, 0.06, base=True, loc=(tx, ty, 0.74), color="#8d5524", kind="gloss")
    K.box(1.55, 0.04, 0.7, base=True, loc=(tx, ty - 0.33, 0.05), color="#6f4518")
    for dx in (-0.76, 0.76):
        K.box(0.06, 0.7, 0.74, base=True, loc=(tx + dx, ty, 0), color="#6f4518")
    for k in range(3):
        K.box(0.4, 0.28, 0.07, base=True, loc=(tx - 0.45, ty, 0.8 + 0.07 * k), rot=(0, 0, 0.1 * k),
              color=("#e63946", "#457b9d", "#2a9d8f")[k])
    K.cyl(0.04, 0.2, seg=8, base=True, loc=(tx + 0.4, ty + 0.1, 0.8), color="#6f4518")
    globe = K.sphere(0.17, seg=16, rings=10, loc=(tx + 0.4, ty + 0.1, 1.16), color="#4895ef", kind="gloss")
    K.spin(globe, 0.1, 2)
    K.sphere(0.07, seg=10, rings=6, loc=(tx + 0.05, ty - 0.15, 0.86), color="#d00000", kind="gloss")
    # students at their desks, looking at the board
    for (sx, sy, rot, kind) in ((-2.6, 2.2, math.pi + 0.45, "girl"), (-1.6, 3.2, math.pi + 0.2, "boy")):
        K.box(0.8, 0.5, 0.05, base=True, loc=(sx, sy + 0.45, 0.62), color="#ced4da")
        for dx in (-0.36, 0.36):
            K.box(0.04, 0.45, 0.62, base=True, loc=(sx + dx, sy + 0.45, 0), color="#6c757d", kind="metal")
        _extra(c, sx, sy, rot, "read", kind=kind, outfit="student", scale=1.0, seated=True, travel=False)
    # window, posters, clock
    wx, wz = 3.6, 2.6
    K.box(1.6, 0.12, 1.6, loc=(wx, 4.42, wz), color="#ffffff", kind="gloss")
    sky = "#0b1d3a" if night else "#9ad1ff"
    for dx in (-0.38, 0.38):
        for dz in (-0.38, 0.38):
            K.box(0.68, 0.05, 0.68, loc=(wx + dx, 4.36, wz + dz), color=sky, kind="emit", emit=0.6 if night else 3.0)
    K.light("AREA", 80 if night else 650, "#9fb4ff" if night else "#fff1d6", loc=(wx, 3.6, wz), target=(0, 0, 1),
            size=2)
    for k, col in enumerate(("#ffadad", "#9bf6ff", "#fdffb6")):
        K.box(0.5, 0.03, 0.65, loc=(-3.6 + 0.6 * k, 4.42, 3.75), color=col)
    clk = P.clock(c)
    clk.root.location = (bx, 4.3, 3.65)
    clk.root.scale = (0.38, 0.38, 0.38)
    K.light("AREA", 300 if not night else 200, "#fff4e6", loc=(0, 0.5, 6.0), size=7)


def _rack(c, x, y, length=2.8, levels=(0.15, 1.45, 2.75, 4.05), depth=1.1):
    for dy in (-length / 2, length / 2):
        for dx in (-depth / 2, depth / 2):
            K.box(0.08, 0.08, 4.6, base=True, loc=(x + dx, y + dy, 0), color="#1d4e89", kind="metal")
    for z in levels:
        for dx in (-depth / 2, depth / 2):
            K.box(0.06, length, 0.1, base=True, loc=(x + dx, y, z), color="#fb8500", kind="metal")
        K.box(depth, length, 0.03, base=True, loc=(x, y, z + 0.1), color="#adb5bd", kind="metal")
        yy = y - length / 2 + 0.08
        while yy < y + length / 2 - 0.5:
            w = c.rng.uniform(0.45, 0.8)
            if c.rng.random() > 0.18:
                hgt = c.rng.uniform(0.4, 0.95)
                K.box(depth * 0.85, w, hgt, base=True, loc=(x, yy + w / 2, z + 0.13),
                      color=c.rng.choice(CARDBOARD), bevel=0.01)
                K.box(depth * 0.86, 0.08, 0.012, base=True, loc=(x, yy + w / 2, z + 0.13 + hgt), color="#e9d8a6")
            yy += w + 0.08


def _forklift(c, x, y, rot):
    f = K.empty("forklift", loc=(x, y, 0), rot=(0, 0, rot))
    p = dict(parent=f)
    yellow = "#ffc300"
    K.box(0.95, 1.3, 0.55, base=True, loc=(0, 0.1, 0.22), color=yellow, kind="gloss", bevel=0.04, **p)
    K.box(0.9, 0.42, 0.55, base=True, loc=(0, 0.6, 0.77), color="#343a40", kind="gloss", **p)
    K.box(0.42, 0.36, 0.1, base=True, loc=(0, 0.25, 0.77), color="#212529", **p)
    K.box(0.42, 0.08, 0.45, base=True, loc=(0, 0.42, 0.87), color="#212529", **p)
    for dx in (-0.42, 0.42):
        for dy in (-0.35, 0.5):
            K.box(0.05, 0.05, 1.35, base=True, loc=(dx, dy, 0.77), color="#212529", kind="metal", **p)
    K.box(0.95, 0.95, 0.05, base=True, loc=(0, 0.07, 2.1), color="#212529", kind="metal", **p)
    for dx in (-0.3, 0.3):
        K.box(0.08, 0.08, 2.3, base=True, loc=(dx, -0.62, 0.1), color="#495057", kind="metal", **p)
    lift = K.empty("carriage", loc=(0, -0.68, 0.15), **p)
    K.animate(lift, lambda t, s: s.loc.__setitem__(2, s.loc.z + 0.6 * K.smooth(0.5 + 0.6 * math.sin(t * 0.5))))
    for dx in (-0.22, 0.22):
        K.box(0.1, 0.9, 0.04, base=True, parent=lift, loc=(dx, -0.45, 0), color="#495057", kind="metal")
    K.box(0.9, 0.9, 0.12, base=True, parent=lift, loc=(0, -0.45, 0.04), color="#a47148")
    for (bx_, by_, bz_) in ((-0.2, -0.25, 0.16), (0.2, -0.25, 0.16), (-0.2, -0.65, 0.16), (0.2, -0.65, 0.16),
                            (0.0, -0.45, 0.56)):
        K.box(0.38, 0.38, 0.38, base=True, parent=lift, loc=(bx_, by_, bz_), color=c.rng.choice(CARDBOARD),
              bevel=0.01)
    for dx in (-0.45, 0.45):
        for dy in (-0.4, 0.55):
            K.cyl(0.2, 0.16, seg=14, loc=(dx, dy, 0.2), rot=(0, math.pi / 2, 0), color="#212529", **p)
    return f


def warehouse(env, T, c):
    night = env.time == "night"
    env.indoor = True
    _fog(T, 0, 1, 0.0)
    K.world_gradient("#cfd4da", "#e9ecef", 0.35)
    K.box(24, 26, 0.2, loc=(0, 6, -0.1), material=K.two_tone_material("concrete", "#b8bec5", "#a3aab2", 0.4, rough=0.7))
    back = 13.0
    K.box(24, 0.3, 9, base=True, loc=(0, back + 0.15, 0), color="#dee2e6")
    for x in (-7.0, 7.0):
        K.box(0.3, 26, 9, base=True, loc=(x, 6, 0), color="#e9ecef")
    for x in (-1.9, 1.9):
        K.box(0.1, 13, 0.005, base=True, loc=(x, 6.5, 0), color="#ffd60a")
    day = not night
    K.box(3.6, 0.05, 3.8, base=True, loc=(0, back - 0.02, 0), color="#fff3d6" if day else "#1b263b", kind="emit",
          emit=2.5 if day else 0.4)
    for k in range(6):
        K.box(3.7, 0.08, 0.13, base=True, loc=(0, back - 0.06, 3.1 + 0.13 * k), color="#adb5bd", kind="metal")
    for x in (-1.9, 1.9):
        K.box(0.2, 0.2, 4.0, base=True, loc=(x, back - 0.1, 0), color="#ffd60a")
    if day:
        K.light("AREA", 900, "#fff1d6", loc=(0, back - 0.4, 2.2), target=(0, 5, 0.5), size=3.5)
    for side in (-1, 1):
        for y0 in (3.2, 6.3, 9.4):
            _rack(c, side * 3.4, y0)
    _forklift(c, 1.0, 8.4, 0.5)
    for (px, py) in ((-1.2, 10.8), (-0.4, 11.6)):
        K.box(1.0, 1.0, 0.12, base=True, loc=(px, py, 0), color="#a47148")
        for k in range(3):
            K.box(0.45, 0.45, 0.4, base=True, loc=(px - 0.24 + 0.24 * (k % 2), py - 0.2 + 0.4 * (k // 2), 0.12),
                  color=c.rng.choice(CARDBOARD), bevel=0.01)
    for y in (3.0, 7.0, 11.0):
        K.cyl(0.01, 2.5, seg=4, base=True, loc=(0, y, 6.3), color="#212529")
        K.hemisphere(0.45, seg=16, rings=6, loc=(0, y, 6.3), rot=(math.pi, 0, 0), color="#343a40", kind="gloss")
        K.sphere(0.12, seg=10, rings=6, loc=(0, y, 6.1), color="#fff3c4", kind="emit", emit=8)
        K.light("POINT", 300 if night else 120, "#ffe8c2", loc=(0, y, 5.9), size=0.3, shadow=False)
    _extra(c, -0.9, 9.6, 0.0, "carry", outfit="worker")
    K.light("AREA", 380, "#fff6ea", loc=(0, 5, 8.5), size=10)


BUILDERS = {
    "village": village, "forest": forest, "city": city, "space": space, "ocean": ocean,
    "desert": desert, "mountains": mountains, "snow": snow, "room": room, "studio": studio,
    "shop": shop, "market": market, "office": office, "cafe": cafe, "classroom": classroom,
    "warehouse": warehouse,
}


def build(name, time, c):
    env = Env(name, time if time in TIMES else "day")
    BUILDERS.get(name, studio)(env, TIMES[env.time], c)
    return env
