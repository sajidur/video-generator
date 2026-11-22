"""Environments: sky, ground, lighting and set dressing around a clear central stage.

Each builder keeps the stage (radius ~3 around the origin) and the corridor
towards the camera (-Y) free, so props and characters stay visible.
"""
import math

import bpy
from mathutils import Vector

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


BUILDERS = {
    "village": village, "forest": forest, "city": city, "space": space, "ocean": ocean,
    "desert": desert, "mountains": mountains, "snow": snow, "room": room, "studio": studio,
}


def build(name, time, c):
    env = Env(name, time if time in TIMES else "day")
    BUILDERS.get(name, studio)(env, TIMES[env.time], c)
    return env
