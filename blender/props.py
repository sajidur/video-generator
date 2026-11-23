"""Procedural low-poly props. Every builder returns Built(root, height, width).

Conventions: Z is up, the camera looks from -Y towards +Y, so "front" is -Y.
Icons are built centred on their root (they float); ground props stand on
z=0; big landmarks and sky props are scaled/placed by the layout code.
"""
import math
from collections import namedtuple

import bmesh
from mathutils import Matrix, Vector

import kit as K

Built = namedtuple("Built", "root height width")
GOLD = "#f5b82e"
PI = math.pi
HALF = PI / 2


def _sparkles(c, parent, n=6, radius=0.9, color="#fff3b0"):
    for i in range(n):
        a = c.rng.uniform(0, K.TAU)
        z = c.rng.uniform(-0.5, 0.7)
        s = K.ico(0.045, sub=1, parent=parent, color=color, kind="emit", emit=8,
                  loc=(radius * math.cos(a), -0.3 + 0.2 * math.sin(a), z))
        K.pulse(s, amp=0.9, speed=c.rng.uniform(0.6, 1.2), phase=c.rng.uniform(0, K.TAU))


# ---------------------------------------------------------------- icons ---


def lightbulb(c):
    root = K.empty("lightbulb")
    glow = K.sphere(0.42, seg=24, rings=14, parent=root, loc=(0, 0, 0.22), color="#ffe9a3",
                    kind="emit", emit=4.0)
    K.cyl(0.2, 0.3, r2=0.3, seg=20, parent=root, loc=(0, 0, -0.17), color="#ffe9a3", kind="emit",
          emit=3.0)
    K.cyl(0.19, 0.28, seg=20, parent=root, loc=(0, 0, -0.45), color="#9aa3ad", kind="metal")
    for z in (-0.38, -0.46, -0.54):
        K.torus(0.19, 0.025, seg=24, rseg=6, parent=root, loc=(0, 0, z), color="#7d8790",
                kind="metal")
    K.cone(0.1, 0.12, seg=12, parent=root, loc=(0, 0, -0.65), rot=(PI, 0, 0), color="#333333")
    lamp = K.light("POINT", 60, "#ffd27a", loc=(0, -0.2, 0.2), size=0.3, shadow=False)
    lamp.parent = root
    K.pulse(glow, amp=0.04, speed=1.2)
    K.sway(root, amp=0.12, speed=0.35, axis=1)
    return Built(root, 1.3, 0.9)


def heart(c):
    root = K.empty("heart")
    pts = []
    for i in range(48):
        t = K.TAU * i / 48
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 28, z / 28 + 0.05))
    h = K.prism(pts, depth=0.32, parent=root, color="#e63946", kind="gloss", bevel=0.05)

    def beat(t, s):
        p = (t * 1.1) % 1.0
        k = 1 + 0.09 * math.exp(-((p - 0.1) / 0.06) ** 2) + 0.06 * math.exp(-((p - 0.3) / 0.06) ** 2)
        s.scale *= k
    K.animate(h, beat)
    _sparkles(c, root, 5, 0.85, "#ffc2d1")
    return Built(root, 1.2, 1.2)


def _star_points(n=5, r_out=0.6, r_in=0.26):
    pts = []
    for i in range(n * 2):
        a = HALF + PI * i / n
        r = r_out if i % 2 == 0 else r_in
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def star(c):
    root = K.empty("star")
    s = K.prism(_star_points(), depth=0.26, parent=root, color=GOLD, kind="metal", bevel=0.03)
    K.spin(s, speed=0.18, axis=2)
    _sparkles(c, root, 7, 0.9)
    return Built(root, 1.2, 1.2)


def dollar(c):
    root = K.empty("dollar")
    t = K.text3d("$", size=1.4, depth=0.22, color=GOLD, kind="metal", parent=root,
                 fontfile=c.font_bold)
    K.spin(t, speed=0.15, axis=2)
    for i in range(3):
        coin = K.cyl(0.16, 0.04, seg=20, parent=root, rot=(HALF, 0, 0), color=GOLD, kind="metal")
        r, ph = 0.85, K.TAU * i / 3

        def orbit(tt, st, ph=ph, r=r):
            a = ph + tt * 1.2
            st.loc = Vector((r * math.cos(a), r * math.sin(a) * 0.5, 0.25 * math.sin(a * 2)))
            st.rot.z += a
        K.animate(coin, orbit)
    return Built(root, 1.4, 1.2)


def lock(c):
    root = K.empty("lock")
    K.box(0.82, 0.36, 0.66, parent=root, loc=(0, 0, -0.22), color=GOLD, kind="metal", bevel=0.06)
    K.torus(0.27, 0.075, seg=20, rseg=10, arc=0.5, parent=root, loc=(0, 0, 0.27),
            rot=(HALF, 0, 0), color="#b8c0c8", kind="metal")
    for x in (-0.27, 0.27):
        K.cyl(0.075, 0.2, seg=10, parent=root, loc=(x, 0, 0.17), color="#b8c0c8", kind="metal")
    K.cyl(0.07, 0.05, seg=16, parent=root, loc=(0, -0.19, -0.15), rot=(HALF, 0, 0), color="#222222")
    K.box(0.06, 0.05, 0.16, parent=root, loc=(0, -0.19, -0.25), color="#222222")
    K.sway(root, amp=0.1, speed=0.4, axis=2)
    return Built(root, 1.2, 0.9)


def magnifier(c):
    root = K.empty("magnifier")
    lens = K.empty("lens", parent=root, rot=(0, 0.6, 0))
    K.torus(0.42, 0.06, seg=32, rseg=10, parent=lens, rot=(HALF, 0, 0), color="#2b2d42", kind="gloss")
    K.cyl(0.4, 0.03, seg=32, parent=lens, rot=(HALF, 0, 0), color="#bde0fe", kind="glass")
    K.segment((0.33, 0, -0.33), (0.75, 0, -0.75), r=0.075, parent=lens, color="#8d5524", kind="gloss")

    def search(t, s):
        s.loc.x += 0.25 * math.sin(t * 1.3)
        s.loc.z += 0.12 * math.sin(t * 2.6)
    K.animate(root, search)
    return Built(root, 1.3, 1.1)


def atom(c):
    root = K.empty("atom")
    for i in range(7):
        d = Vector((c.rng.uniform(-1, 1), c.rng.uniform(-1, 1), c.rng.uniform(-1, 1)))
        d = d.normalized() * 0.1 if d.length else d
        K.sphere(0.12, seg=12, rings=8, parent=root, loc=d,
                 color="#ef476f" if i % 2 else "#118ab2", kind="gloss")
    for i in range(3):
        ring = K.empty("ring", parent=root, rot=(1.2, 0, i * PI / 3))
        K.torus(0.68, 0.014, seg=48, rseg=6, parent=ring, color="#4cc9f0", kind="emit", emit=3)
        e = K.sphere(0.06, seg=10, rings=6, parent=ring, color="#a0f0ff", kind="emit", emit=8)

        def orbit(t, s, ph=i * 2.1):
            a = ph + t * 2.4
            s.loc = Vector((0.68 * math.cos(a), 0.68 * math.sin(a), 0))
        K.animate(e, orbit)
    K.spin(root, speed=0.06, axis=2)
    return Built(root, 1.4, 1.4)


def dna(c):
    root = K.empty("dna")
    helix = K.empty("helix", parent=root)
    n = 14
    for i in range(n):
        a = i * 0.5
        z = (i - n / 2) * 0.11
        p1 = Vector((0.36 * math.cos(a), 0.36 * math.sin(a), z))
        p2 = Vector((-p1.x, -p1.y, z))
        K.sphere(0.075, seg=10, rings=6, parent=helix, loc=p1, color="#4cc9f0", kind="gloss")
        K.sphere(0.075, seg=10, rings=6, parent=helix, loc=p2, color="#f72585", kind="gloss")
        K.segment(p1, p2, r=0.022, seg=6, parent=helix, color="#e9ecef", kind="gloss")
    K.spin(helix, speed=0.2, axis=2)
    root.rotation_euler = (0, 0.25, 0)
    return Built(root, 1.6, 0.9)


def virus(c):
    root = K.empty("virus")
    K.ico(0.45, sub=2, parent=root, color="#7bd389", kind="gloss", smooth=True)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    dirs = [v.co.copy() for v in bm.verts]
    bm.free()
    for d in dirs:
        K.segment(d * 0.4, d * 0.62, r=0.028, seg=6, parent=root, color="#5aa469", kind="matte")
        K.sphere(0.06, seg=8, rings=6, parent=root, loc=d * 0.64, color="#e63946", kind="gloss")
    K.spin(root, speed=0.07, axis=2)
    K.pulse(root, amp=0.03, speed=0.8)
    return Built(root, 1.3, 1.3)


def _gear_points(teeth, r_out, r_in):
    pts = []
    for i in range(teeth):
        a0 = K.TAU * i / teeth
        step = K.TAU / teeth
        for frac, r in ((0.0, r_in), (0.15, r_out), (0.45, r_out), (0.6, r_in)):
            a = a0 + step * frac
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def gear(c):
    root = K.empty("gear")
    specs = ((12, 0.62, 0.5, (-0.2, 0, 0.12), "#adb5bd", 0.12),
             (8, 0.4, 0.3, (0.62, -0.05, -0.38), GOLD, -0.18))
    for teeth, ro, ri, loc, col, speed in specs:
        g = K.empty("g", parent=root, loc=loc)
        K.prism(_gear_points(teeth, ro, ri), depth=0.18, parent=g, color=col, kind="metal",
                bevel=0.015)
        K.cyl(ro * 0.28, 0.24, seg=16, parent=g, rot=(HALF, 0, 0), color="#495057", kind="metal")
        K.spin(g, speed=speed, axis=1)
    return Built(root, 1.3, 1.5)


def clock(c):
    root = K.empty("clock")
    K.cyl(0.6, 0.14, seg=40, parent=root, rot=(HALF, 0, 0), color="#fdfcf7", kind="gloss")
    K.torus(0.6, 0.07, seg=40, rseg=10, parent=root, rot=(HALF, 0, 0), color=c.accent, kind="gloss")
    for i in range(12):
        a = K.TAU * i / 12
        big = i % 3 == 0
        K.box(0.04 if big else 0.025, 0.02, 0.12 if big else 0.07, parent=root,
              loc=(0.47 * math.sin(a), -0.08, 0.47 * math.cos(a)), rot=(0, a, 0), color="#222222")
    for length, width, speed in ((0.3, 0.05, 0.03), (0.44, 0.032, 0.3)):
        piv = K.empty("hand", parent=root, loc=(0, -0.09, 0))
        K.box(width, 0.02, length, parent=piv, loc=(0, 0, length / 2 - 0.05), color="#222222")
        K.spin(piv, speed=speed, axis=1)
    K.sphere(0.05, seg=10, rings=6, parent=root, loc=(0, -0.11, 0), color=c.accent, kind="gloss")
    for side in (-1, 1):
        K.hemisphere(0.2, parent=root, loc=(side * 0.38, 0.02, 0.5), rot=(0, side * 0.6, 0),
                     color=c.accent, kind="metal")
    K.sway(root, amp=0.06, speed=1.0, axis=1)
    return Built(root, 1.4, 1.3)


def trophy(c):
    root = K.empty("trophy")
    K.box(0.55, 0.55, 0.14, parent=root, loc=(0, 0, -0.62), color="#3d2b1f", kind="gloss",
          bevel=0.02)
    K.box(0.32, 0.32, 0.1, parent=root, loc=(0, 0, -0.5), color=GOLD, kind="metal")
    K.cyl(0.07, 0.3, seg=12, parent=root, loc=(0, 0, -0.3), color=GOLD, kind="metal")
    K.cyl(0.14, 0.12, r2=0.06, seg=20, parent=root, loc=(0, 0, -0.15), color=GOLD, kind="metal")
    K.cyl(0.18, 0.62, r2=0.42, seg=28, base=True, parent=root, loc=(0, 0, -0.1), color=GOLD,
          kind="metal", smooth=True)
    for side in (-1, 1):
        K.torus(0.16, 0.035, seg=20, rseg=8, parent=root, loc=(side * 0.42, 0, 0.25),
                rot=(HALF, 0, 0), color=GOLD, kind="metal")
    K.prism(_star_points(5, 0.11, 0.05), depth=0.04, parent=root, loc=(0, -0.33, 0.25),
            rot=(-0.25, 0, 0), color="#ffffff", kind="emit", emit=2)
    K.spin(root, speed=0.08, axis=2)
    _sparkles(c, root, 8, 0.8)
    return Built(root, 1.4, 1.0)


def question(c):
    root = K.empty("question")
    t = K.text3d("?", size=1.5, depth=0.24, color=c.accent, kind="gloss", parent=root,
                 fontfile=c.font_bold)
    K.sway(t, amp=0.18, speed=0.4, axis=2)
    return Built(root, 1.4, 0.8)


def medical(c):
    root = K.empty("medical")
    cross = K.empty("cross", parent=root, loc=(-0.15, 0, 0.12))
    K.box(0.72, 0.22, 0.24, parent=cross, color="#e63946", kind="gloss", bevel=0.04)
    K.box(0.24, 0.22, 0.72, parent=cross, color="#e63946", kind="gloss", bevel=0.04)
    K.pulse(cross, amp=0.05, speed=0.9)
    pill = K.empty("pill", parent=root, loc=(0.5, -0.1, -0.4), rot=(0, 0.8, 0))
    K.cyl(0.11, 0.22, seg=16, base=True, parent=pill, color="#ffffff", kind="gloss")
    K.cyl(0.11, 0.22, seg=16, top=True, parent=pill, color="#4cc9f0", kind="gloss")
    K.hemisphere(0.11, parent=pill, loc=(0, 0, 0.22), color="#ffffff", kind="gloss")
    K.hemisphere(0.11, parent=pill, loc=(0, 0, -0.22), rot=(PI, 0, 0), color="#4cc9f0", kind="gloss")
    K.sway(pill, amp=0.3, speed=0.5, axis=1)
    return Built(root, 1.3, 1.2)


def speech_bubble(c):
    root = K.empty("speech_bubble")
    K.box(1.15, 0.3, 0.75, parent=root, color="#ffffff", kind="gloss", bevel=0.14)
    K.cone(0.16, 0.38, seg=4, parent=root, loc=(-0.3, 0, -0.45), rot=(PI, -0.5, 0), color="#ffffff",
           kind="gloss")
    for i, x in enumerate((-0.28, 0, 0.28)):
        d = K.sphere(0.08, seg=12, rings=8, parent=root, loc=(x, -0.17, 0), color=c.accent,
                     kind="gloss")

        def hop(t, s, ph=i * 0.25):
            s.loc.z += 0.09 * max(0.0, math.sin(K.TAU * (t * 0.9 - ph)))
        K.animate(d, hop)
    K.sway(root, amp=0.08, speed=0.4, axis=1)
    return Built(root, 1.2, 1.2)


def shield(c):
    root = K.empty("shield")
    pts = [(-0.5, 0.45), (-0.25, 0.52), (0, 0.55), (0.25, 0.52), (0.5, 0.45), (0.5, 0.05),
           (0.42, -0.22), (0.24, -0.44), (0, -0.62), (-0.24, -0.44), (-0.42, -0.22), (-0.5, 0.05)]
    K.prism(pts, depth=0.18, parent=root, color="#3a86ff", kind="metal", bevel=0.04)
    K.prism(_star_points(5, 0.25, 0.11), depth=0.08, parent=root, loc=(0, -0.11, 0),
            color=GOLD, kind="metal")
    K.sway(root, amp=0.15, speed=0.35, axis=2)
    _sparkles(c, root, 5, 0.8, "#cfe1ff")
    return Built(root, 1.3, 1.1)


def lightning(c):
    root = K.empty("lightning")
    pts = [(-0.05, 0.7), (0.35, 0.7), (0.1, 0.15), (0.38, 0.15), (-0.2, -0.75), (-0.02, -0.05),
           (-0.3, -0.05)]
    b = K.prism(pts, depth=0.2, parent=root, color="#ffd60a", kind="emit", emit=3.5, bevel=0.02)
    K.flicker(b, amp=0.08, speed=6.0)
    lamp = K.light("POINT", 40, "#ffd60a", loc=(0, -0.4, 0), size=0.3, shadow=False)
    lamp.parent = root
    return Built(root, 1.5, 0.8)


# --------------------------------------------------------------- ground ---


def tree(c, color=None):
    root = K.empty("tree")
    greens = ["#52b788", "#40916c", "#74c69d", "#2d6a4f"]
    K.cyl(0.13, 0.95, r2=0.08, seg=7, base=True, parent=root, color="#7f5539")
    canopy = K.empty("canopy", parent=root, loc=(0, 0, 1.25))
    for loc, r in (((0, 0, 0), 0.6), ((0.28, 0.08, 0.28), 0.45), ((-0.25, -0.05, 0.24), 0.42)):
        K.ico(r, sub=1, jitter=0.12, rng=c.rng, parent=canopy, loc=loc,
              color=color or c.rng.choice(greens))
    K.sway(canopy, amp=0.025, speed=0.3, axis=1, phase=c.rng.uniform(0, K.TAU))
    return Built(root, 2.0, 1.3)


def pine_tree(c, snowy=False):
    root = K.empty("pine")
    K.cyl(0.1, 0.45, seg=6, base=True, parent=root, color="#6f4518")
    green = c.rng.choice(["#2d6a4f", "#1b4332", "#40916c"])
    for i, (r, h, z) in enumerate(((0.72, 0.9, 0.35), (0.56, 0.8, 0.8), (0.4, 0.7, 1.22))):
        K.cone(r, h, seg=7, base=True, parent=root, loc=(0, 0, z), color=green)
        if snowy:
            K.cone(r * 0.55, h * 0.5, seg=7, base=True, parent=root, loc=(0, 0, z + h * 0.48),
                   color="#f8f9fa")
    K.sway(root, amp=0.015, speed=0.3, axis=1, phase=c.rng.uniform(0, K.TAU))
    return Built(root, 2.0, 1.4)


def house(c):
    root = K.empty("house")
    wall = c.rng.choice(["#f4e9cd", "#ffd6a5", "#caf0f8", "#ffcad4", "#e9edc9"])
    roof = c.rng.choice(["#bc4749", "#9c6644", "#6d597a", "#c1121f"])
    K.box(1.6, 1.3, 1.1, base=True, parent=root, color=wall)
    r = K.prism([(-0.82, 0), (0.82, 0), (0, 0.72)], depth=1.85, parent=root, loc=(0, 0, 1.1),
                rot=(0, 0, HALF), color=roof)
    r.scale = (1.0, 1.0, 1.0)
    K.box(0.18, 0.18, 0.5, base=True, parent=root, loc=(0.45, 0.25, 1.35), color="#8d6e63")
    K.box(0.36, 0.06, 0.66, base=True, parent=root, loc=(0, -0.65, 0), color="#6b4226")
    win = dict(kind="emit", emit=3.0, color="#ffd27a") if c.night else dict(color="#a2d2ff",
                                                                             kind="gloss")
    for x in (-0.5, 0.5):
        K.box(0.32, 0.06, 0.3, parent=root, loc=(x, -0.65, 0.65), **win)
    return Built(root, 1.9, 1.9)


def car(c):
    root = K.empty("car")
    body = K.empty("body", parent=root)
    col = c.rng.choice(["#e63946", "#3a86ff", "#ffbe0b", "#2a9d8f", "#ff006e"])
    K.box(1.5, 0.72, 0.36, parent=body, loc=(0, 0, 0.36), color=col, kind="gloss", bevel=0.08)
    K.box(0.82, 0.64, 0.32, parent=body, loc=(-0.1, 0, 0.68), color="#1d3557", kind="gloss",
          bevel=0.08)
    for y in (-0.2, 0.2):
        K.box(0.04, 0.12, 0.08, parent=body, loc=(0.75, y, 0.4), color="#fff3b0", kind="emit",
              emit=4 if c.night else 1)
    wheels = []
    for x in (-0.48, 0.48):
        for y in (-0.36, 0.36):
            w = K.empty("wheel", parent=root, loc=(x, y, 0.18))
            K.cyl(0.18, 0.14, seg=14, parent=w, rot=(HALF, 0, 0), color="#212529")
            K.cyl(0.08, 0.16, seg=8, parent=w, rot=(HALF, 0, 0), color="#adb5bd", kind="metal")
            wheels.append(w)
    speed = 1.0
    mid = c.t0 + (c.dur - c.t0) / 2

    def drive(t, s):
        s.loc.x += speed * (t - mid)
    K.animate(root, drive)
    for w in wheels:
        K.animate(w, lambda t, s: s.rot.__setitem__(1, s.rot.y + speed * (t - mid) / 0.18))
    K.animate(body, lambda t, s: s.loc.__setitem__(2, s.loc.z + 0.012 * math.sin(t * 17)))
    return Built(root, 0.9, 1.6)


def rocket(c):
    root = K.empty("rocket")
    K.cyl(0.65, 0.12, seg=24, base=True, parent=root, color="#6c757d", kind="metal")
    ship = K.empty("ship", parent=root, loc=(0, 0, 0.12))
    K.cyl(0.28, 1.3, seg=20, base=True, parent=ship, loc=(0, 0, 0.35), color="#f8f9fa", kind="gloss",
          smooth=True)
    K.cone(0.28, 0.55, seg=20, base=True, parent=ship, loc=(0, 0, 1.65), color="#e63946",
           kind="gloss", smooth=True)
    K.cyl(0.2, 0.25, r2=0.26, seg=16, base=True, parent=ship, loc=(0, 0, 0.12), color="#343a40",
          kind="metal")
    K.torus(0.11, 0.03, seg=20, rseg=6, parent=ship, loc=(0, -0.27, 1.3), rot=(HALF, 0, 0),
            color="#adb5bd", kind="metal")
    K.cyl(0.1, 0.03, seg=16, parent=ship, loc=(0, -0.27, 1.3), rot=(HALF, 0, 0), color="#4cc9f0",
          kind="emit", emit=1.5)
    for i in range(3):
        a = K.TAU * i / 3 + HALF
        K.prism([(0, 0), (0.35, -0.1), (0.35, 0.15), (0, 0.6)], depth=0.05, parent=ship,
                loc=(0.22 * math.cos(a), 0.22 * math.sin(a), 0.3), rot=(0, 0, a),
                color="#e63946", kind="gloss")
    flame = K.empty("flame", parent=ship, loc=(0, 0, 0.1))
    f1 = K.cone(0.2, 0.75, seg=12, parent=flame, rot=(PI, 0, 0), loc=(0, 0, -0.3), color="#ff7b00",
                kind="emit", emit=6)
    f2 = K.cone(0.12, 0.5, seg=12, parent=flame, rot=(PI, 0, 0), loc=(0, 0, -0.22), color="#ffd60a",
                kind="emit", emit=10)
    K.flicker(f1, 0.25, 9, 1.0)
    K.flicker(f2, 0.25, 11, 2.0)
    lamp = K.light("POINT", 150, "#ff9e40", loc=(0, 0, -0.3), size=0.4, shadow=False)
    lamp.parent = flame
    launch = c.t0 + max(1.5, (c.dur - c.t0) * 0.45)

    def ignite(t, s):
        s.scale *= 0.35 + 0.65 * K.smooth((t - launch + 1.2) / 1.0)
    K.animate(flame, ignite)

    def fly(t, s):
        dt = t - launch
        if dt > 0:
            s.loc.z += 0.9 * dt * dt
        s.loc.x += 0.01 * math.sin(t * 40) * (1 if dt > -1.2 else 0)
    K.animate(ship, fly)
    for i in range(10):
        a = K.TAU * i / 10
        p = K.ico(0.25, sub=1, parent=root, loc=(0, 0, 0.2), color="#dee2e6", jitter=0.1, rng=c.rng)

        def puff(t, s, a=a):
            k = K.ease_out((t - launch + 0.8) / 2.5)
            s.loc += Vector((math.cos(a), math.sin(a) * 0.6, 0.15)) * 1.4 * k
            s.scale *= max(1e-4, k * 1.8)
        K.animate(p, puff)
    return Built(root, 2.4, 1.3)


def books(c):
    root = K.empty("books")
    covers = ["#e63946", "#457b9d", "#2a9d8f", "#f4a261", "#6d597a"]
    z = 0.0
    for i in range(4):
        w, d, h = c.rng.uniform(0.95, 1.15), c.rng.uniform(0.7, 0.8), c.rng.uniform(0.13, 0.18)
        b = K.empty("book", parent=root, loc=(c.rng.uniform(-0.06, 0.06), 0, z),
                    rot=(0, 0, c.rng.uniform(-0.25, 0.25)))
        col = covers[i % len(covers)]
        K.box(w, d, 0.025, parent=b, loc=(0, 0, 0.0125), color=col, kind="gloss")
        K.box(w, d, 0.025, parent=b, loc=(0, 0, h - 0.0125), color=col, kind="gloss")
        K.box(0.03, d, h, base=True, parent=b, loc=(-w / 2 + 0.015, 0, 0), color=col, kind="gloss")
        K.box(w - 0.05, d - 0.04, h - 0.04, base=True, parent=b, loc=(0.02, 0, 0.02),
              color="#fdfcdc")
        delay = c.t0 + 0.25 * i

        def drop(t, s, delay=delay):
            x = (t - delay) / 0.5
            if x < 0:
                s.scale *= 1e-4
            elif x < 1:
                s.loc.z += 3.0 * (1 - K.clamp(x)) ** 2
            else:
                s.loc.z += 0.06 * abs(math.sin((x - 1) * 6)) * math.exp(-(x - 1) * 3)
        K.animate(b, drop)
        z += h
    return Built(root, z + 0.2, 1.2)


def coins(c):
    root = K.empty("coins")
    stacks = (((-0.45, 0.1), 6), ((0.0, -0.15), 10), ((0.45, 0.15), 14))
    k = 0
    for (x, y), n in stacks:
        for j in range(n):
            coin = K.cyl(0.2, 0.05, seg=20, parent=root, color=GOLD, kind="metal",
                         loc=(x + c.rng.uniform(-0.02, 0.02), y + c.rng.uniform(-0.02, 0.02),
                              0.025 + j * 0.052))
            K.pop(coin, delay=c.t0 + 0.08 * k, dur=0.35)
            k += 1
    _sparkles(c, root, 6, 0.8)
    return Built(root, 0.9, 1.3)


def laptop(c):
    root = K.empty("laptop")
    K.box(1.3, 0.85, 0.06, base=True, parent=root, color="#ced4da", kind="metal", bevel=0.02)
    K.box(1.1, 0.4, 0.01, base=True, parent=root, loc=(0, 0.08, 0.06), color="#343a40")
    hinge = K.empty("hinge", parent=root, loc=(0, 0.42, 0.06), rot=(-0.25, 0, 0))
    K.box(1.3, 0.05, 0.85, base=True, parent=hinge, color="#ced4da", kind="metal", bevel=0.02)
    K.box(1.18, 0.01, 0.74, base=True, parent=hinge, loc=(0, -0.03, 0.055), color="#14213d",
          kind="emit", emit=1.5)
    cols = ["#4cc9f0", "#f72585", "#ffd60a", "#80ffdb", "#b8c0ff"]
    for i in range(7):
        w = c.rng.uniform(0.25, 0.8)
        indent = c.rng.choice((0, 0.08, 0.16))
        line = K.box(w, 0.012, 0.04, parent=hinge, color=cols[i % len(cols)], kind="emit", emit=3,
                     loc=(-0.5 + indent + w / 2, -0.04, 0.7 - i * 0.085))
        d0 = c.t0 + 0.3 * i

        def type_in(t, s, d0=d0, w=w):
            k = K.clamp((t - d0) / 0.35)
            s.scale.x *= max(k, 1e-4)
            s.loc.x -= w / 2 * (1 - k)
        K.animate(line, type_in)
    return Built(root, 0.95, 1.4)


def phone(c):
    root = K.empty("phone")
    body = K.empty("body", parent=root, loc=(0, 0, 0.08), rot=(-0.18, 0, 0))
    K.box(0.66, 0.09, 1.3, base=True, parent=body, color="#212529", kind="gloss", bevel=0.07)
    K.box(0.58, 0.01, 1.16, base=True, parent=body, loc=(0, -0.05, 0.07), color="#1b263b",
          kind="emit", emit=1.2)
    cols = ["#ff006e", "#3a86ff", "#ffbe0b", "#06d6a0", "#8338ec", "#fb5607"]
    k = 0
    for row in range(4):
        for col in range(3):
            icon = K.box(0.12, 0.02, 0.12, parent=body, color=cols[k % len(cols)], kind="emit",
                         emit=2, loc=(-0.17 + col * 0.17, -0.06, 1.05 - row * 0.19), bevel=0.02)
            K.pop(icon, delay=c.t0 + 0.07 * k, dur=0.35)
            k += 1
    bubble = K.box(0.42, 0.03, 0.12, parent=body, loc=(0, -0.08, 0.3), color="#ffffff", kind="emit",
                   emit=1.5, bevel=0.03)
    K.pop(bubble, delay=c.t0 + 1.6, dur=0.5)
    K.sway(body, amp=0.06, speed=0.3, axis=2)
    return Built(root, 1.5, 0.8)


def bar_chart(c):
    root = K.empty("bar_chart")
    K.box(1.8, 0.6, 0.06, base=True, parent=root, color="#e9ecef", kind="gloss")
    cols = ["#4361ee", "#4895ef", "#4cc9f0", "#06d6a0", "#80ed99"]
    heights = (0.35, 0.6, 0.9, 1.25, 1.65)
    tops = []
    for i, h in enumerate(heights):
        x = -0.68 + i * 0.34
        bar = K.box(0.24, 0.3, h, base=True, parent=root, loc=(x, 0, 0.06), color=cols[i],
                    kind="gloss", bevel=0.02)
        d0 = c.t0 + 0.25 * i

        def grow(t, s, d0=d0):
            s.scale.z *= max(1e-4, K.ease_out((t - d0) / 0.7))
        K.animate(bar, grow)
        tops.append(Vector((x, -0.3, 0.06 + h + 0.25)))
    arrow = K.empty("arrow", parent=root)
    for a, b in zip(tops, tops[1:]):
        K.segment(a, b, r=0.035, parent=arrow, color="#ff4d6d", kind="emit", emit=2)
    tip = K.cone(0.1, 0.24, seg=10, parent=arrow, loc=tops[-1] + Vector((0.08, 0, 0.1)),
                 color="#ff4d6d", kind="emit", emit=2)
    tip.rotation_euler = (tops[-1] - tops[-2]).to_track_quat("Z", "Y").to_euler()
    K.pop(arrow, delay=c.t0 + 1.4, dur=0.6)
    return Built(root, 2.0, 1.9)


def campfire(c):
    root = K.empty("campfire")
    for i in range(9):
        a = K.TAU * i / 9
        K.ico(0.12, sub=1, jitter=0.2, rng=c.rng, parent=root, loc=(0.5 * math.cos(a), 0.5 * math.sin(a), 0.05),
              color="#6c757d")
    for i in range(4):
        a = PI * i / 4
        log = K.cyl(0.07, 0.85, seg=7, parent=root, loc=(0, 0, 0.12), color="#7f4f24")
        log.rotation_euler = (1.25, 0, a)
    fl = K.empty("flames", parent=root, loc=(0, 0, 0.1))
    for r, h, col, emit, off in ((0.24, 0.8, "#ff5400", 5, (0, 0)), (0.16, 0.6, "#ffbd00", 8, (0.05, -0.03)),
                                  (0.13, 0.5, "#ff8500", 6, (-0.1, 0.04))):
        f = K.cone(r, h, seg=9, base=True, parent=fl, loc=(off[0], off[1], 0), color=col, kind="emit",
                   emit=emit)
        K.flicker(f, 0.3, 7 + r * 10, r * 30)
    lamp = K.light("POINT", 120, "#ff8c42", loc=(0, 0, 0.6), size=0.3, shadow=True)
    lamp.parent = root
    K.every_frame(lambda t: setattr(lamp.data, "energy", 120 * (1 + 0.25 * K.wobble(t, 3, 4))))
    for i in range(8):
        e = K.ico(0.025, sub=1, parent=root, color="#ffb703", kind="emit", emit=10)
        ph, x0 = c.rng.uniform(0, 1), c.rng.uniform(-0.2, 0.2)

        def rise(t, s, ph=ph, x0=x0):
            u = (t * 0.6 + ph) % 1.0
            s.loc = Vector((x0 + 0.15 * math.sin(u * 9), 0, 0.3 + u * 1.8))
            s.scale *= max(1e-4, 1 - u)
        K.animate(e, rise)
    return Built(root, 1.0, 1.1)


def flag(c):
    root = K.empty("flag")
    K.ico(0.6, sub=1, jitter=0.15, rng=c.rng, parent=root, scale=(1, 1, 0.45), color="#6c757d")
    K.cyl(0.03, 2.1, seg=8, base=True, parent=root, loc=(0, 0, 0.15), color="#adb5bd", kind="metal")
    K.sphere(0.05, parent=root, loc=(0, 0, 2.27), color=GOLD, kind="metal")
    bm = bmesh.new()
    nx, nz, w, h = 12, 7, 0.95, 0.58
    vs = [[bm.verts.new((w * i / nx, 0, -h * j / nz)) for j in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nz):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    cloth = K.mesh_object("cloth", bm, parent=root, loc=(0.02, 0, 2.2), color=c.accent, kind="matte")
    me = cloth.data
    rest = [v.co.copy() for v in me.vertices]

    def wave(t):
        for v, r in zip(me.vertices, rest):
            k = r.x / w
            v.co.y = 0.09 * k * math.sin(5.5 * r.x - 6.0 * t)
            v.co.z = r.z - 0.04 * k * (1 + math.sin(3 * r.x - 4 * t))
        me.update()
    K.every_frame(wave)
    return Built(root, 2.3, 1.3)


def boat(c):
    root = K.empty("boat")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 1.5
        v.co.y *= 0.55
        v.co.z = v.co.z * 0.32 + 0.16
        if v.co.x > 0.5:
            v.co.y *= 0.15
            v.co.z += 0.08
        if v.co.z < 0.1:
            v.co.y *= 0.55
            v.co.x *= 0.85
    K.mesh_object("hull", bm, parent=root, color="#9c6644")
    K.cyl(0.03, 1.5, seg=8, base=True, parent=root, loc=(-0.05, 0, 0.3), color="#6f4518")
    K.prism([(0, 0), (0.62, 0), (0, 1.25)], depth=0.02, parent=root, loc=(-0.02, 0, 0.45),
            color="#f8f9fa")
    K.bob(root, amp=0.05, speed=0.35)
    K.sway(root, amp=0.06, speed=0.3, axis=0)
    K.drift(root, (0.12, 0, 0))
    return Built(root, 1.8, 1.6)


def wind_turbine(c):
    root = K.empty("wind_turbines")
    for (x, y, s) in ((0.0, 0.0, 1.0), (-2.2, 3.0, 0.9), (2.6, 5.0, 0.85)):
        t = K.empty("turbine", parent=root, loc=(x, y, 0), scale=s)
        K.cyl(0.09, 3.0, r2=0.05, seg=10, base=True, parent=t, color="#f8f9fa", kind="gloss")
        K.box(0.18, 0.4, 0.18, parent=t, loc=(0, 0.05, 3.05), color="#f8f9fa", kind="gloss")
        hub = K.empty("hub", parent=t, loc=(0, -0.18, 3.05))
        K.sphere(0.1, seg=10, rings=6, parent=hub, color="#dee2e6", kind="gloss")
        for i in range(3):
            K.box(0.08, 0.02, 1.25, parent=hub, loc=(0, 0, 0), rot=(0, K.TAU * i / 3, 0),
                  color="#f8f9fa", kind="gloss").data.transform(Matrix.Translation((0, 0, 0.65)))
        K.spin(hub, speed=0.35 + 0.05 * x, axis=1)
    return Built(root, 3.8, 1.5)


def flowers(c):
    root = K.empty("flowers")
    cols = ["#ff006e", "#ffbe0b", "#fb5607", "#8338ec", "#ff8fab", "#ffffff"]
    for i in range(11):
        a, r = c.rng.uniform(0, K.TAU), c.rng.uniform(0.1, 0.9)
        f = K.empty("flower", parent=root, loc=(r * math.cos(a), r * math.sin(a), 0))
        h = c.rng.uniform(0.25, 0.5)
        K.cyl(0.015, h, seg=5, base=True, parent=f, color="#52b788")
        col = c.rng.choice(cols)
        for k in range(5):
            b = K.TAU * k / 5
            K.sphere(0.055, seg=8, rings=5, parent=f, loc=(0.06 * math.cos(b), 0.06 * math.sin(b), h),
                     scale=(1, 1, 0.5), color=col)
        K.sphere(0.04, seg=8, rings=5, parent=f, loc=(0, 0, h + 0.02), color="#ffd60a")
        K.sway(f, amp=0.08, speed=0.5, axis=1, phase=c.rng.uniform(0, K.TAU))
        K.pop(f, delay=c.t0 + 0.1 * i, dur=0.4)
    return Built(root, 0.6, 1.8)


def rocks(c):
    root = K.empty("rocks")
    for i in range(5):
        a = c.rng.uniform(0, K.TAU)
        r = 0 if i == 0 else c.rng.uniform(0.5, 1.0)
        size = 0.55 if i == 0 else c.rng.uniform(0.15, 0.35)
        K.ico(size, sub=1, jitter=0.25, rng=c.rng, parent=root, loc=(r * math.cos(a), r * math.sin(a), size * 0.4),
              scale=(1, 1, 0.7), color=c.rng.choice(["#6c757d", "#868e96", "#495057"]))
    return Built(root, 0.8, 1.8)


# what the other people do while the hero does something (the hero talks -> they listen)
PARTNER_REACTS = {"talk": "listen", "point": "listen", "announce": "listen", "give": "buy", "buy": "give",
                  "shake_hands": "shake_hands", "listen": "talk", "drink": "drink", "thumbs_up": "talk",
                  "write": "talk", "phone": "idle", "clap": "celebrate", "celebrate": "clap", "sad": "talk",
                  "think": "talk", "shrug": "talk"}
CROWD_REACTS = {"talk": ["listen", "thumbs_up", "listen", "clap", "listen"],
                "point": ["listen", "listen", "thumbs_up", "listen", "listen"],
                "announce": ["listen", "clap", "wave", "listen", "thumbs_up"],
                "celebrate": ["clap", "celebrate", "clap", "wave", "celebrate"],
                "give": ["phone", "listen", "buy", "listen", "wave"]}


def crowd(c):
    import character
    root = K.empty("crowd")
    acts = CROWD_REACTS.get(getattr(c, "hero_action", ""), ["idle", "wave", "celebrate", "idle", "wave"])
    for i, x in enumerate((-1.6, -0.8, 0.0, 0.8, 1.6)):
        look = character.random_look(c.rng)
        ch = character.build(look, c, loc=(x, 0.4 * abs(x), 0), scale=0.85)
        ch["root"].parent = root
        character.act(ch, acts[i], c, phase=c.rng.uniform(0, 3), travel=False)
    return Built(root, 1.6, 3.8)


def person(c):
    """One other person (customer, friend, parent...). The layout turns them towards the hero,
    and they react to what the hero does (the hero sells -> they pay, the hero talks -> they listen)."""
    import random

    import character
    root = K.empty("person")
    action = PARTNER_REACTS.get(getattr(c, "hero_action", ""), "talk")
    partner = getattr(c, "partner", None)  # the video's cast member: same face in every shot
    if partner:
        look = character.random_look(random.Random(partner["seed"]), partner["type"])
        look.update({k: v for k, v in (partner.get("look") or {}).items() if k in look and k != "type"})
        outfit = partner.get("outfit", "casual")
        if action == "give" and getattr(c, "env_name", "") in ("shop", "market", "cafe"):
            outfit = "shopkeeper"  # whoever sells here wears the apron
    else:
        look = character.random_look(c.rng, c.rng.choice(["man", "woman", "old_man", "old_woman"]))
        outfit = "casual"
    ch = character.build(look, c, outfit=outfit)
    ch["root"].parent = root
    character.act(ch, action, c, phase=1.3, travel=False, hand=1, voice=getattr(c, "partner_voice", None))
    return Built(root, 2.05, 0.9)


def signpost(c):
    root = K.empty("signpost")
    K.cyl(0.06, 2.3, seg=8, base=True, parent=root, color="#7f5539")
    cols = [c.accent, "#2a9d8f", "#457b9d"]
    shape = [(-0.5, -0.11), (0.38, -0.11), (0.55, 0), (0.38, 0.11), (-0.5, 0.11)]
    for i, (z, ang) in enumerate(((2.0, 0.2), (1.65, PI - 0.3), (1.3, 0.5))):
        arm = K.empty("arm", parent=root, loc=(0, 0, z), rot=(0, 0, ang))
        K.prism(shape, depth=0.06, parent=arm, loc=(0.48, 0, 0), color=cols[i], kind="gloss",
                bevel=0.015)
        K.sway(arm, amp=0.05, speed=0.4, axis=2, phase=i)
    return Built(root, 2.3, 1.6)


def stairs(c):
    root = K.empty("stairs")
    cols = ["#4361ee", "#4895ef", "#4cc9f0", "#06d6a0", "#80ed99"]
    for i in range(5):
        h = 0.25 * (i + 1)
        st = K.box(0.5, 0.8, h, base=True, parent=root, loc=(-1.0 + i * 0.5, 0, 0), color=cols[i],
                   kind="gloss", bevel=0.02)
        K.pop(st, delay=c.t0 + 0.2 * i, dur=0.45)
    s = K.prism(_star_points(5, 0.25, 0.11), depth=0.1, parent=root, loc=(1.0, 0, 1.65),
                color=GOLD, kind="emit", emit=2.5)
    K.spin(s, speed=0.3, axis=2)
    K.pop(s, delay=c.t0 + 1.2, dur=0.6)
    return Built(root, 2.0, 2.6)


def factory(c):
    root = K.empty("factory")
    K.box(2.2, 1.3, 1.1, base=True, parent=root, color="#8d99ae")
    for i in range(3):
        K.prism([(0, 0), (0.73, 0), (0.73, 0.45)], depth=1.3, parent=root, loc=(-1.1 + i * 0.73, 0, 1.1),
                color="#5c677d")
    for x in (-0.6, 0.0, 0.6):
        K.box(0.35, 0.05, 0.3, parent=root, loc=(x, -0.66, 0.55),
              **(dict(color="#ffd27a", kind="emit", emit=3) if c.night else dict(color="#a2d2ff", kind="gloss")))
    for k, x in enumerate((0.55, 0.95)):
        h = 1.9 - 0.3 * k
        K.cyl(0.14, h, r2=0.11, seg=10, base=True, parent=root, loc=(x, 0.3, 0.8), color="#c1121f")
        K.cyl(0.125, 0.15, seg=10, base=True, parent=root, loc=(x, 0.3, 0.8 + h * 0.55), color="#f8f9fa")
        for i in range(6):
            p = K.ico(0.2, sub=1, jitter=0.15, rng=c.rng, parent=root, color="#adb5bd")
            top = Vector((x, 0.3, 0.8 + h))

            def smoke(t, s, ph=i / 6, top=top):
                u = (t * 0.25 + ph) % 1.0
                s.loc = top + Vector((u * 1.2, u * 0.4, u * 2.0))
                s.scale *= max(1e-4, 0.4 + 2.2 * u) * (1 - u ** 4)
            K.animate(p, smoke)
    return Built(root, 2.8, 2.4)


# ------------------------------------------------------------------ big ---


def height_material(name, stops):
    """Colour by object-space height: stops = [(z, '#hex'), ...]."""
    def build(nt, bsdf):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        lo, hi = stops[0][0], stops[-1][0]
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["From Min"].default_value = lo
        rng.inputs["From Max"].default_value = hi
        nt.links.new(sep.outputs["Z"], rng.inputs["Value"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        els = ramp.color_ramp.elements
        while len(els) < len(stops):
            els.new(0.5)
        for el, (z, col) in zip(els, stops):
            el.position = (z - lo) / (hi - lo)
            el.color = (*K.lin(col), 1)
        nt.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.85
    return K.custom_material(name, build)


def _radial_mesh(name, R, profile, res=36, rng=None, rough=0.25, **kw):
    def h(x, y):
        r = math.hypot(x, y) / R
        if r >= 1:
            return -0.3
        n = K.noise.noise(Vector((x * 0.6, y * 0.6, 3.1))) if rough else 0
        return max(-0.3, profile(r) + n * rough * (1 - r) * R * 0.25)
    return K.grid(size=R, res=res, height=h, name=name, **kw)


def mountain(c):
    root = K.empty("mountain")
    mat = height_material("mountain", [(0.0, "#5f6f52"), (1.6, "#7d8597"), (4.6, "#f8f9fa")])
    for (x, y, s) in ((0, 0, 1.0), (-6.5, 3, 0.7), (6.0, 2, 0.6)):
        K_m = _radial_mesh("peak", 6.0, lambda r: 7.0 * (1 - r) ** 1.4, rough=0.35, material=mat,
                           parent=root, loc=(x, y, 0), scale=s)
        K_m.rotation_euler.z = c.rng.uniform(0, K.TAU)
    return Built(root, 7.0, 14.0)


def volcano(c):
    root = K.empty("volcano")
    mat = height_material("volcano", [(0.0, "#6b705c"), (1.5, "#5e503f"), (4.2, "#3d3129")])
    rc = 0.17

    def prof(r):
        top = 5.5 * (1 - rc) ** 1.2
        return 5.5 * (1 - r) ** 1.2 if r > rc else top - (rc - r) * 6

    _radial_mesh("cone", 6.0, prof, res=44, rough=0.2, material=mat, parent=root)
    crater_z = 5.5 * (1 - rc) ** 1.2
    lava = K.cyl(0.9, 0.3, seg=16, parent=root, loc=(0, 0, crater_z - 0.35), color="#ff5400",
                 kind="emit", emit=8)
    K.pulse(lava, 0.05, 1.5)
    lamp = K.light("POINT", 1500, "#ff6d00", loc=(0, 0, crater_z + 1), size=1.0, shadow=False)
    lamp.parent = root
    K.every_frame(lambda t: setattr(lamp.data, "energy", 1500 * (1 + 0.3 * K.wobble(t, 5, 3))))
    for i in range(16):
        b = K.ico(0.16, sub=1, parent=root, color=c.rng.choice(["#ff7b00", "#ffb700", "#ff5400"]),
                  kind="emit", emit=9)
        v = Vector((c.rng.uniform(-1.6, 1.6), c.rng.uniform(-1.2, 1.2), c.rng.uniform(5, 8)))
        ph = c.rng.uniform(0, 1)

        def fly(t, s, v=v, ph=ph):
            u = ((t / 1.8) + ph) % 1.0 * 1.8
            p = Vector((v.x * u, v.y * u, crater_z + v.z * u - 4.9 * u * u))
            s.loc = p
            if p.z < crater_z - 2:
                s.scale *= 1e-4
        K.animate(b, fly)
    for i in range(8):
        p = K.ico(0.9, sub=1, jitter=0.2, rng=c.rng, parent=root, color="#495057")

        def smoke(t, s, ph=i / 8):
            u = (t * 0.12 + ph) % 1.0
            s.loc = Vector((u * 3.5, u * 1.5, crater_z + 0.5 + u * 6))
            s.scale *= max(1e-4, 0.5 + 2.5 * u) * (1 - u ** 4)
        K.animate(p, smoke)
    return Built(root, 8.0, 12.0)


def pyramid(c):
    root = K.empty("pyramids")
    for (x, y, s) in ((0, 0, 1.0), (-4.5, 3.5, 0.7), (4.0, 5.0, 0.55)):
        K.cone(3.2, 3.4, seg=4, base=True, parent=root, loc=(x, y, 0), rot=(0, 0, PI / 4), scale=s,
               color="#e9c46a")
    return Built(root, 3.4, 10.0)


def window_material(night):
    def build(nt, bsdf):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        nt.links.new(sep.outputs["X"], add.inputs[0])
        nt.links.new(sep.outputs["Y"], add.inputs[1])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(add.outputs[0], comb.inputs["X"])
        nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.offset = 0.0
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Mortar Size"].default_value = 0.09
        brick.inputs["Brick Width"].default_value = 0.42
        brick.inputs["Row Height"].default_value = 0.5
        brick.inputs["Bias"].default_value = 0.0
        brick.inputs["Color1"].default_value = (1, 1, 1, 1)
        brick.inputs["Color2"].default_value = (0, 0, 0, 1)
        brick.inputs["Mortar"].default_value = (*K.lin("#adb5bd"), 1)
        nt.links.new(comb.outputs["Vector"], brick.inputs["Vector"])
        glass = (*K.lin("#22344f" if night else "#8ecae6"), 1)
        mixc = nt.nodes.new("ShaderNodeMix")
        mixc.data_type = "RGBA"
        nt.links.new(brick.outputs["Fac"], mixc.inputs["Factor"])
        mixc.inputs["A"].default_value = glass
        mixc.inputs["B"].default_value = (*K.lin("#ced4da"), 1)
        nt.links.new(mixc.outputs["Result"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.35
        if night:
            lit = nt.nodes.new("ShaderNodeMath")
            lit.operation = "GREATER_THAN"
            lit.inputs[1].default_value = 0.55
            bw = nt.nodes.new("ShaderNodeRGBToBW")
            nt.links.new(brick.outputs["Color"], bw.inputs["Color"])
            nt.links.new(bw.outputs["Val"], lit.inputs[0])
            inv = nt.nodes.new("ShaderNodeMath")
            inv.operation = "SUBTRACT"
            inv.inputs[0].default_value = 1.0
            nt.links.new(brick.outputs["Fac"], inv.inputs[1])
            m = nt.nodes.new("ShaderNodeMath")
            m.operation = "MULTIPLY"
            nt.links.new(lit.outputs[0], m.inputs[0])
            nt.links.new(inv.outputs[0], m.inputs[1])
            s = nt.nodes.new("ShaderNodeMath")
            s.operation = "MULTIPLY"
            s.inputs[1].default_value = 3.0
            nt.links.new(m.outputs[0], s.inputs[0])
            bsdf.inputs["Emission Color"].default_value = (*K.lin("#ffd27a"), 1)
            nt.links.new(s.outputs[0], bsdf.inputs["Emission Strength"])
    return K.custom_material("windows_night" if night else "windows_day", build)


def tower(c, parent, loc, w, d, h):
    mat = window_material(c.night)
    K.box(w, d, h, base=True, parent=parent, loc=loc, material=mat, color="#ffffff")
    K.box(w * 1.04, d * 1.04, 0.2, base=True, parent=parent, loc=(loc[0], loc[1], h), color="#6c757d")


def buildings(c):
    root = K.empty("buildings")
    spots = [(-5.5, 1.0), (-3.2, 3.0), (-1.0, 0.0), (1.4, 2.5), (3.6, 0.5), (5.8, 3.0), (0.2, 5.5),
             (-2.2, 6.5), (3.0, 7.0)]
    for x, y in spots:
        tower(c, root, (x, y, 0), c.rng.uniform(1.4, 2.2), c.rng.uniform(1.4, 2.2), c.rng.uniform(4, 11))
    return Built(root, 10.0, 13.0)


# ------------------------------------------------------------------ sky ---


def sun(c):
    root = K.empty("sun")
    s = K.sphere(1.2, seg=32, rings=16, parent=root, color="#ffcf56", kind="emit", emit=12)
    K.pulse(s, 0.02, 0.3)
    return Built(root, 2.4, 2.4)


def moon(c):
    root = K.empty("moon")
    K.sphere(1.0, seg=32, rings=16, parent=root, color="#f1f0e8", kind="emit", emit=1.6)
    for i in range(6):
        a, b = c.rng.uniform(-0.8, 0.8), c.rng.uniform(-0.7, 0.7)
        p = Vector((a, -1.0, b)).normalized() * 0.97
        cr = K.cyl(c.rng.uniform(0.1, 0.2), 0.05, seg=14, parent=root, loc=p, color="#cfcfc4",
                   kind="emit", emit=1.1)
        cr.rotation_euler = p.to_track_quat("Z", "Y").to_euler()
    return Built(root, 2.0, 2.0)


def planet(c):
    root = K.empty("planet")
    body = K.empty("body", parent=root, rot=(0.35, 0.2, 0))

    def build(nt, bsdf):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "MULTIPLY_ADD"
        nt.links.new(nz.outputs["Fac"], add.inputs[0])
        add.inputs[1].default_value = 0.25
        nt.links.new(sep.outputs["Z"], add.inputs[2])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        els = ramp.color_ramp.elements
        cols = ["#e9c46a", "#f4a261", "#e76f51", "#f4a261", "#fefae0"]
        while len(els) < len(cols):
            els.new(0.5)
        for i, (el, col) in enumerate(zip(els, cols)):
            el.position = i / (len(cols) - 1)
            el.color = (*K.lin(col), 1)
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["From Min"].default_value = -1.2
        rng.inputs["From Max"].default_value = 1.4
        nt.links.new(add.outputs[0], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    s = K.sphere(1.1, seg=40, rings=20, parent=body, material=K.custom_material("planet", build))
    K.spin(s, 0.05, 2)
    K.torus(1.75, 0.32, seg=64, rseg=6, parent=body, scale=(1, 1, 0.04), color="#d4a373")
    return Built(root, 2.6, 4.0)


def earth(c):
    root = K.empty("earth")

    def build(nt, bsdf):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 1.6
        nz.inputs["Detail"].default_value = 5.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (*K.lin("#1d70b8"), 1)
        ramp.color_ramp.elements[1].position = 0.55
        ramp.color_ramp.elements[1].color = (*K.lin("#52b788"), 1)
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        ab = nt.nodes.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        nt.links.new(sep.outputs["Z"], ab.inputs[0])
        pole = nt.nodes.new("ShaderNodeMath")
        pole.operation = "GREATER_THAN"
        pole.inputs[1].default_value = 0.92
        nt.links.new(ab.outputs[0], pole.inputs[0])
        mixc = nt.nodes.new("ShaderNodeMix")
        mixc.data_type = "RGBA"
        nt.links.new(pole.outputs[0], mixc.inputs["Factor"])
        nt.links.new(ramp.outputs["Color"], mixc.inputs["A"])
        mixc.inputs["B"].default_value = (1, 1, 1, 1)
        nt.links.new(mixc.outputs["Result"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.5
    globe = K.empty("globe", parent=root, rot=(0.4, 0, 0))
    s = K.sphere(1.1, seg=48, rings=24, parent=globe, material=K.custom_material("earth", build))
    K.spin(s, 0.06, 2)
    K.sphere(1.17, seg=48, rings=24, parent=globe, color="#90e0ef", kind="glass")
    for i in range(5):
        cl = K.ico(0.18, sub=1, parent=globe, color="#ffffff", scale=(1.6, 1, 0.5))
        a, b = c.rng.uniform(0, K.TAU), c.rng.uniform(-0.6, 0.6)
        p = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))) * 1.13
        cl.location = p
        cl.rotation_euler = p.to_track_quat("Z", "Y").to_euler()
    return Built(root, 2.4, 2.4)


def clouds(c):
    root = K.empty("clouds")
    for i in range(5):
        cl = K.empty("cloud", parent=root, loc=(c.rng.uniform(-9, 9), c.rng.uniform(-2, 4),
                                                c.rng.uniform(-1.0, 1.5)))
        for k in range(4):
            K.ico(c.rng.uniform(0.5, 0.9), sub=2, parent=cl, loc=(k * 0.7 - 1.0, c.rng.uniform(-0.2, 0.2),
                                                               c.rng.uniform(0, 0.35)),
                  scale=(1, 1, 0.75), color="#ffffff", kind="emit", emit=0.35)
        K.drift(cl, (c.rng.uniform(0.15, 0.35), 0, 0))
    return Built(root, 2.0, 18.0)


def birds(c):
    root = K.empty("birds")
    for i in range(6):
        row = (i + 1) // 2
        side = -1 if i % 2 else 1
        b = K.empty("bird", parent=root, loc=(-row * 0.9, side * row * 0.7, -row * 0.15))
        K.sphere(0.12, seg=8, rings=6, parent=b, scale=(2.2, 1, 0.8), color="#2b2d42")
        for s in (-1, 1):
            wing = K.empty("wing", parent=b)
            K.box(0.3, 0.6, 0.03, parent=wing, loc=(0, s * 0.32, 0), color="#2b2d42")

            def flap(t, st, s=s, ph=i * 0.7):
                st.rot.x += s * 0.6 * math.sin(t * 9 + ph)
            K.animate(wing, flap)
        K.bob(b, 0.08, 0.6, i)
    K.drift(root, (1.3, 0, 0))
    return Built(root, 1.0, 4.0)


def airplane(c):
    root = K.empty("airplane")
    K.cyl(0.26, 2.6, seg=16, parent=root, rot=(0, HALF, 0), color="#f8f9fa", kind="gloss", smooth=True)
    K.sphere(0.26, seg=16, rings=8, parent=root, loc=(1.3, 0, 0), scale=(1.5, 1, 1), color="#f8f9fa",
             kind="gloss")
    K.box(0.6, 3.0, 0.07, parent=root, loc=(0.1, 0, -0.08), color="#dee2e6", kind="gloss")
    K.box(0.35, 1.1, 0.05, parent=root, loc=(-1.2, 0, 0.05), color="#dee2e6", kind="gloss")
    K.prism([(0, 0), (0.5, 0), (0.15, 0.6)], depth=0.05, parent=root, loc=(-1.45, 0, 0.15),
            color=c.accent, kind="gloss")
    for x in (-0.6, -0.2, 0.2, 0.6):
        K.box(0.12, 0.02, 0.08, parent=root, loc=(x, -0.26, 0.06), color="#1d3557", kind="gloss")
    K.drift(root, (2.0, 0, 0.12))
    K.sway(root, 0.05, 0.3, 0)
    return Built(root, 1.0, 3.0)


# ------------------------------------------------------- business icons ---

PRODUCT_COLS = ["#e63946", "#f4a261", "#2a9d8f", "#457b9d", "#ffb703", "#8338ec", "#ff006e", "#06d6a0",
                "#fb5607", "#3a86ff", "#f8f9fa"]
CARDBOARD = ["#c8a165", "#d4a373", "#bc8a5f", "#cfa46a"]


def _heart_pts(s=1.0):
    pts = []
    for i in range(32):
        t = K.TAU * i / 32
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 28 * s, (z / 28 + 0.05) * s))
    return pts


def _wedge(name, r, h, a0, a1, seg=40, **kw):
    """Solid pie slice between angles a0 and a1 (radians), from z=0 to z=h."""
    bm = bmesh.new()
    n = max(2, int(seg * (a1 - a0) / K.TAU) + 2)
    bottom = [bm.verts.new((0, 0, 0))]
    top = [bm.verts.new((0, 0, h))]
    for i in range(n):
        a = a0 + (a1 - a0) * i / (n - 1)
        bottom.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0)))
        top.append(bm.verts.new((r * math.cos(a), r * math.sin(a), h)))
    bm.faces.new(list(reversed(bottom)))
    bm.faces.new(top)
    for i in range(len(bottom)):
        j = (i + 1) % len(bottom)
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return K.mesh_object(name, bm, **kw)


def _drop_in(ob, delay, height=2.5):
    def drop(t, s):
        x = (t - delay) / 0.5
        if x < 0:
            s.scale *= 1e-4
        elif x < 1:
            s.loc.z += height * (1 - K.clamp(x)) ** 2
        else:
            s.loc.z += 0.05 * abs(math.sin((x - 1) * 6)) * math.exp(-(x - 1) * 3)
    K.animate(ob, drop)


def megaphone(c):
    root = K.empty("megaphone")
    horn = K.empty("horn", parent=root, rot=(0, 0, -0.55))
    K.cyl(0.4, 0.75, r2=0.13, seg=28, parent=horn, loc=(0.2, 0, 0), rot=(0, -HALF, 0), color=c.accent,
          kind="gloss")
    K.cyl(0.35, 0.03, seg=28, parent=horn, loc=(0.5, 0, 0), rot=(0, HALF, 0), color="#495057")
    K.torus(0.4, 0.035, seg=28, rseg=6, parent=horn, loc=(0.58, 0, 0), rot=(0, HALF, 0), color="#343a40",
            kind="gloss")
    K.cyl(0.11, 0.3, seg=16, parent=horn, loc=(-0.3, 0, 0), rot=(0, HALF, 0), color="#343a40", kind="gloss")
    K.box(0.09, 0.09, 0.36, parent=horn, loc=(-0.05, 0, -0.3), rot=(0, 0.25, 0), color="#343a40",
          kind="gloss", bevel=0.02)
    for i in range(3):
        ring = K.torus(0.42, 0.03, seg=32, rseg=6, parent=horn, loc=(0.7, 0, 0), rot=(0, HALF, 0),
                       color=c.accent, kind="emit", emit=3)

        def wave(t, s, ph=i / 3):
            u = (t * 0.9 + ph) % 1.0
            s.loc.x += u * 1.1
            s.scale *= max(1e-4, (0.6 + 1.1 * u) * (1 - u ** 3))
        K.animate(ring, wave)
    K.sway(horn, amp=0.08, speed=0.5, axis=1)
    return Built(root, 1.2, 1.8)


def target(c):
    root = K.empty("target")
    board = K.empty("board", parent=root, rot=(HALF, 0, 0))
    cols = ["#e63946", "#f8f9fa", "#e63946", "#f8f9fa", "#e63946"]
    for i, r in enumerate((0.62, 0.5, 0.38, 0.26, 0.13)):
        K.cyl(r, 0.08 + 0.025 * i, seg=40, parent=board, color=cols[i], kind="gloss")
    K.torus(0.63, 0.035, seg=40, rseg=6, parent=board, color="#343a40", kind="gloss")
    d = Vector((0.35, -1.0, 0.3)).normalized()
    arrow = K.empty("arrow", parent=root, loc=(0.0, -0.1, 0.0))
    arrow.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    K.cyl(0.022, 0.9, seg=8, base=True, parent=arrow, color="#7f5539")
    K.cone(0.05, 0.14, seg=10, parent=arrow, loc=(0, 0, -0.02), rot=(PI, 0, 0), color="#adb5bd", kind="metal")
    for k in range(3):
        K.prism([(0, 0), (0.12, 0.06), (0.12, 0.22), (0, 0.2)], depth=0.01, parent=arrow, loc=(0, 0, 0.68),
                rot=(0, 0, K.TAU * k / 3), color=c.accent, kind="gloss")
    hit = c.t0 + 0.45

    def fly(t, s):
        if t < c.t0:
            s.scale *= 1e-4
        k = K.clamp((t - c.t0) / 0.45)
        s.loc += d * 2.5 * (1 - k) ** 2
        dt = t - hit
        if dt > 0:
            s.rot.x += 0.12 * math.sin(dt * 40) * math.exp(-dt * 5)
    K.animate(arrow, fly)
    return Built(root, 1.3, 1.3)


def price_tag(c):
    root = K.empty("price_tag")
    pivot = K.empty("pivot", parent=root, loc=(0, 0, 0.55))
    K.torus(0.06, 0.012, seg=16, rseg=5, parent=pivot, rot=(HALF, 0, 0), color="#f8f9fa")
    K.cyl(0.008, 0.3, seg=6, top=True, parent=pivot, loc=(0, 0, -0.06), color="#f8f9fa")
    tag = K.empty("tag", parent=pivot, loc=(-0.092, 0, -0.21), rot=(0, 1.0, 0))
    pts = [(0, 0), (0.22, 0.2), (0.95, 0.2), (0.95, -0.2), (0.22, -0.2)]
    K.prism(pts, depth=0.06, parent=tag, color="#ff595e", kind="gloss", bevel=0.01)
    K.torus(0.045, 0.015, seg=16, rseg=5, parent=tag, loc=(0.17, 0, 0), rot=(HALF, 0, 0), color=GOLD,
            kind="metal")
    K.text3d("%", size=0.3, depth=0.02, color="#ffffff", kind="gloss", fontfile=c.font_bold, parent=tag,
             loc=(0.6, -0.04, 0), rot=(HALF, -1.0, 0))
    K.sway(pivot, amp=0.18, speed=0.45, axis=1)
    _sparkles(c, root, 4, 0.7)
    return Built(root, 1.2, 1.0)


def pie_chart(c):
    root = K.empty("pie_chart")
    tilt = K.empty("tilt", parent=root, loc=(0, 0, -0.12), rot=(1.0, 0, 0))
    spin = K.empty("spin", parent=tilt)
    K.spin(spin, speed=0.04, axis=2)
    fracs = [0.38, 0.27, 0.2, 0.15]
    cols = ["#4361ee", "#4cc9f0", c.accent, "#f72585"]
    a = 0.0
    for i, (f, col) in enumerate(zip(fracs, cols)):
        a1 = a + f * K.TAU
        mid = (a + a1) / 2
        sl = K.empty("slice", parent=spin)
        _wedge("slice", 0.62, 0.22, a + 0.015, a1 - 0.015, parent=sl, color=col, kind="gloss")
        out = Vector((math.cos(mid), math.sin(mid), 0))
        d0 = c.t0 + 0.2 * i

        def anim(t, s, d0=d0, out=out, pull=(i == 2)):
            s.scale *= max(1e-4, K.ease_out_back((t - d0) / 0.5) if t > d0 else 0.0)
            if pull:
                e = K.smooth((t - d0 - 1.0) / 0.6)
                s.loc += out * 0.22 * e
                s.loc.z += 0.12 * e
        K.animate(sl, anim)
        a = a1
    return Built(root, 1.2, 1.4)


def gift(c):
    root = K.empty("gift")
    body = K.empty("box", parent=root, loc=(0, 0, -0.4))
    col = c.rng.choice(["#e63946", "#4361ee", "#8338ec", "#06d6a0"])
    rib = "#ffd166"
    K.box(0.62, 0.62, 0.5, base=True, parent=body, color=col, kind="gloss", bevel=0.02)
    K.box(0.12, 0.64, 0.51, base=True, parent=body, color=rib, kind="gloss")
    K.box(0.64, 0.12, 0.51, base=True, parent=body, color=rib, kind="gloss")
    lid = K.empty("lid", parent=body, loc=(0, 0, 0.5))
    K.box(0.7, 0.7, 0.14, base=True, parent=lid, color=col, kind="gloss", bevel=0.02)
    K.box(0.13, 0.72, 0.15, base=True, parent=lid, color=rib, kind="gloss")
    K.box(0.72, 0.13, 0.15, base=True, parent=lid, color=rib, kind="gloss")
    for s in (-1, 1):
        K.torus(0.13, 0.035, seg=20, rseg=6, parent=lid, loc=(s * 0.12, 0, 0.25), rot=(HALF, s * 0.5, 0),
                color=rib, kind="gloss")
    K.sphere(0.06, seg=10, rings=6, parent=lid, loc=(0, 0, 0.18), color=rib, kind="gloss")

    def hop(t, s):
        u = (t * 0.7) % 1.0
        s.loc.z += 0.16 * math.sin(u * PI * 2) if u < 0.5 else 0.0
    K.animate(lid, hop)
    _sparkles(c, root, 6, 0.75)
    K.sway(root, amp=0.12, speed=0.3, axis=2)
    return Built(root, 1.2, 0.9)


def magnet(c):
    root = K.empty("magnet")
    mag = K.empty("mag", parent=root, loc=(-0.45, 0, 0), rot=(0, -HALF, 0))
    R, r = 0.3, 0.11
    K.torus(R, r, seg=24, rseg=10, arc=0.5, parent=mag, rot=(HALF, 0, 0), color="#e63946", kind="gloss")
    for x in (-R, R):
        K.cyl(r, 0.3, seg=14, top=True, parent=mag, loc=(x, 0, 0), color="#e63946", kind="gloss")
        K.cyl(r, 0.16, seg=14, top=True, parent=mag, loc=(x, 0, -0.3), color="#dee2e6", kind="metal")
    K.sway(mag, amp=0.06, speed=0.8, axis=1)
    cols = ["#4cc9f0", "#ffd166", "#06d6a0", "#f72585", "#8338ec", "#ff9f1c"]
    for i in range(6):
        p = K.empty("fan", parent=root)
        K.sphere(0.06, seg=10, rings=6, parent=p, loc=(0, 0, 0.14), color="#ffdbac")
        K.cone(0.08, 0.17, seg=10, parent=p, color=cols[i])
        z0, y0 = c.rng.uniform(-0.45, 0.45), c.rng.uniform(-0.3, 0.3)

        def pull(t, s, z0=z0, y0=y0, ph=i / 6):
            u = (t * 0.35 + ph) % 1.0
            e = u * u
            s.loc = Vector((1.9 - 1.75 * e, y0 * (1 - e), z0 * (1 - e)))
            s.scale *= max(1e-4, min(1.0, u * 6) * (1 - max(0.0, (u - 0.9) * 10)))
        K.animate(p, pull)
    return Built(root, 1.0, 2.4)


def rating(c):
    root = K.empty("rating")
    K.box(2.5, 0.08, 0.7, parent=root, color="#ffffff", kind="gloss", bevel=0.03)
    for i in range(5):
        st = K.prism(_star_points(5, 0.21, 0.09), depth=0.08, parent=root, loc=(-0.96 + i * 0.48, -0.08, 0),
                     color=GOLD, kind="emit", emit=2.2)
        K.pop(st, delay=c.t0 + 0.25 + 0.18 * i, dur=0.45)
        K.bob(st, 0.02, 0.8, i)
    _sparkles(c, root, 5, 1.3)
    return Built(root, 0.8, 2.5)


def likes(c):
    root = K.empty("likes")
    specs = (("#ff006e", "heart", (-0.42, 0.28)), ("#3a86ff", "user", (0.4, 0.45)),
             ("#06d6a0", "share", (0.06, -0.32)))
    for i, (col, icon, (x, z)) in enumerate(specs):
        b = K.empty("badge", parent=root, loc=(x, 0, z))
        K.box(0.52, 0.1, 0.42, parent=b, color=col, kind="gloss", bevel=0.05)
        K.prism([(-0.08, -0.2), (0.08, -0.2), (0.0, -0.33)], depth=0.1, parent=b, color=col, kind="gloss")
        w = dict(parent=b, color="#ffffff", kind="emit", emit=1.5)
        if icon == "heart":
            K.prism(_heart_pts(0.42), depth=0.03, loc=(0, -0.06, -0.02), **w)
        elif icon == "user":
            K.sphere(0.07, seg=12, rings=8, loc=(0, -0.06, 0.06), **w)
            K.hemisphere(0.12, seg=12, rings=6, loc=(0, -0.06, -0.14), scale=(1, 0.3, 0.8), **w)
        else:
            pts = [Vector((-0.12, -0.06, 0)), Vector((0.1, -0.06, 0.1)), Vector((0.1, -0.06, -0.1))]
            for p in pts:
                K.sphere(0.04, seg=10, rings=6, loc=p, **w)
            for p in pts[1:]:
                K.segment(pts[0], p, r=0.012, **w)
        K.pop(b, delay=c.t0 + 0.3 + 0.35 * i, dur=0.5)
        K.bob(b, 0.05, 0.5, i * 1.7)
    for i in range(6):
        h = K.prism(_heart_pts(0.25), depth=0.03, parent=root, color="#ff4d6d", kind="emit", emit=2)
        x0 = c.rng.uniform(-0.7, 0.7)

        def rise(t, s, ph=i / 6, x0=x0):
            u = (t * 0.45 + ph) % 1.0
            s.loc = Vector((x0 + 0.1 * math.sin(u * 8), -0.12, -0.7 + 1.7 * u))
            s.scale *= max(1e-4, math.sin(u * PI))
        K.animate(h, rise)
    return Built(root, 1.4, 1.4)


def balance(c):
    root = K.empty("balance")
    base = K.empty("base", parent=root, loc=(0, 0, -0.78))
    K.cyl(0.32, 0.08, seg=24, base=True, parent=base, color=GOLD, kind="metal")
    K.cyl(0.04, 1.3, seg=10, base=True, parent=base, loc=(0, 0, 0.08), color=GOLD, kind="metal")
    K.sphere(0.07, seg=12, rings=8, parent=base, loc=(0, 0, 1.42), color=GOLD, kind="metal")
    beam = K.empty("beam", parent=base, loc=(0, 0, 1.34))
    K.box(1.5, 0.05, 0.05, parent=beam, color=GOLD, kind="metal")
    tilt = lambda t: 0.16 * math.sin(K.TAU * 0.25 * t)  # noqa: E731
    K.animate(beam, lambda t, s: s.rot.__setitem__(1, s.rot.y + tilt(t)))
    for side in (-1, 1):
        hang = K.empty("hang", parent=beam, loc=(side * 0.72, 0, 0))
        K.animate(hang, lambda t, s: s.rot.__setitem__(1, s.rot.y - tilt(t)))
        for k in range(3):
            a = K.TAU * k / 3
            K.segment((0, 0, 0), (0.22 * math.cos(a), 0.22 * math.sin(a), -0.55), r=0.008, parent=hang,
                      color="#adb5bd", kind="metal")
        K.cyl(0.3, 0.04, seg=24, parent=hang, loc=(0, 0, -0.57), color=GOLD, kind="metal")
        if side < 0:
            for j in range(4):
                K.cyl(0.1, 0.035, seg=16, parent=hang, loc=(0, 0, -0.53 + j * 0.037), color="#ffd166",
                      kind="metal")
        else:
            K.box(0.22, 0.22, 0.22, base=True, parent=hang, loc=(0, 0, -0.55), color=c.accent, kind="gloss",
                  bevel=0.02)
    return Built(root, 1.6, 1.9)


# ------------------------------------------------------- business ground ---


def shopping_bag(c):
    root = K.empty("shopping_bag")
    specs = ((-0.32, 0.05, 0.42, 0.52, "#e76f51"), (0.18, -0.05, 0.38, 0.62, "#2a9d8f"),
             (0.02, 0.32, 0.46, 0.48, "#e9c46a"))
    for i, (x, y, w, h, col) in enumerate(specs):
        b = K.empty("bag", parent=root, loc=(x, y, 0), rot=(0, 0, c.rng.uniform(-0.3, 0.3)))
        K.box(w, 0.22, h, base=True, parent=b, color=col)
        K.box(w + 0.006, 0.226, 0.06, base=True, parent=b, loc=(0, 0, h - 0.06), color=K.shade(col, 0.8))
        for yy in (-0.08, 0.08):
            K.torus(0.1, 0.012, seg=16, rseg=5, arc=0.5, parent=b, loc=(0, yy, h), rot=(HALF, 0, 0),
                    color=K.shade(col, 0.6))
        if i == 0:
            for k in range(3):
                K.ico(0.09, sub=1, parent=b, loc=(-0.08 + 0.08 * k, 0, h + 0.04), scale=(1, 1, 1.4),
                      color="#52b788")
        elif i == 1:
            K.cyl(0.05, 0.42, seg=10, parent=b, loc=(0.06, 0, h + 0.05), rot=(0, 0.35, 0), color="#d4a373")
        else:
            K.cyl(0.05, 0.2, seg=10, base=True, parent=b, loc=(0.1, 0, h - 0.1), color="#4361ee", kind="gloss")
            K.cyl(0.022, 0.08, seg=8, base=True, parent=b, loc=(0.1, 0, h + 0.1), color="#f8f9fa")
        K.pop(b, delay=c.t0 + 0.15 * i, dur=0.45)
    return Built(root, 0.9, 1.1)


def shopping_cart(c):
    root = K.empty("shopping_cart")
    metal = dict(parent=root, color="#ced4da", kind="metal")
    L, W, z0, z1 = 0.95, 0.6, 0.42, 0.95
    for i in range(9):
        x = -L / 2 + L * i / 8
        for y in (-W / 2, W / 2):
            K.segment((x, y, z0), (x, y, z1), r=0.008, **metal)
    for j in range(1, 4):
        y = -W / 2 + W * j / 4
        for x in (-L / 2, L / 2):
            K.segment((x, y, z0), (x, y, z1), r=0.008, **metal)
    corners = [(-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)]
    for z in (z0, (z0 + z1) / 2, z1):
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            K.segment((a[0], a[1], z), (b[0], b[1], z), r=0.012, **metal)
    K.box(L, W, 0.01, loc=(0, 0, z0), **metal)
    for y in (-W / 2, W / 2):
        K.segment((-L / 2, y, z1), (-L / 2 - 0.18, y, z1 + 0.1), r=0.012, **metal)
    K.cyl(0.03, W + 0.05, seg=10, parent=root, loc=(-L / 2 - 0.18, 0, z1 + 0.1), rot=(HALF, 0, 0),
          color="#e63946", kind="gloss")
    for x in (-L / 2 + 0.08, L / 2 - 0.08):
        for y in (-W / 2 + 0.05, W / 2 - 0.05):
            K.segment((x, y, z0), (x, y, 0.12), r=0.014, **metal)
            K.cyl(0.07, 0.04, seg=12, parent=root, loc=(x, y, 0.07), rot=(HALF, 0, 0), color="#212529")
    K.box(L - 0.16, W - 0.1, 0.01, loc=(0, 0, 0.18), **metal)
    for i in range(7):
        x, y = c.rng.uniform(-0.33, 0.33), c.rng.uniform(-0.2, 0.2)
        col = c.rng.choice(PRODUCT_COLS)
        if i % 3 == 2:
            K.cyl(0.05, 0.3, seg=10, base=True, parent=root, loc=(x, y, z0), color=col, kind="gloss")
        else:
            K.box(c.rng.uniform(0.14, 0.24), c.rng.uniform(0.12, 0.2), c.rng.uniform(0.25, 0.45), base=True,
                  parent=root, loc=(x, y, z0), rot=(0, 0, c.rng.uniform(-0.4, 0.4)), color=col, kind="gloss")
    return Built(root, 1.2, 1.3)


def boxes(c):
    root = K.empty("boxes")
    specs = (((-0.36, 0.0, 0.0), (0.66, 0.55, 0.48)), ((0.34, 0.05, 0.0), (0.6, 0.5, 0.52)),
             ((-0.05, 0.02, 0.52), (0.62, 0.5, 0.42)), ((0.66, -0.45, 0.0), (0.34, 0.3, 0.3)))
    for i, ((x, y, z), (w, d, h)) in enumerate(specs):
        b = K.empty("box", parent=root, loc=(x, y, z), rot=(0, 0, c.rng.uniform(-0.12, 0.12)))
        K.box(w, d, h, base=True, parent=b, color=CARDBOARD[i % len(CARDBOARD)], bevel=0.01)
        K.box(0.1, d + 0.004, 0.012, parent=b, loc=(0, 0, h), color="#e9d8a6")
        K.box(0.1, 0.006, h * 0.3, base=True, parent=b, loc=(0, -d / 2 - 0.002, h * 0.7), color="#e9d8a6")
        K.box(w * 0.36, 0.006, h * 0.28, base=True, parent=b, loc=(-w * 0.22, -d / 2 - 0.003, h * 0.12),
              color="#ffffff")
        for k in range(6):
            K.box(0.008 if k % 2 else 0.014, 0.008, h * 0.14, base=True, parent=b,
                  loc=(-w * 0.34 + k * 0.025, -d / 2 - 0.005, h * 0.15), color="#212529")
        _drop_in(b, c.t0 + 0.2 * i)
    return Built(root, 1.0, 1.5)


def truck(c):
    root = K.empty("truck")
    body = K.empty("body", parent=root)
    cab = c.rng.choice(["#e63946", "#3a86ff", "#ff9f1c", "#2a9d8f"])
    K.box(2.5, 0.95, 0.14, parent=body, loc=(0.1, 0, 0.42), color="#343a40")
    K.box(1.7, 1.06, 1.3, base=True, parent=body, loc=(-0.35, 0, 0.49), color="#f8f9fa", kind="gloss",
          bevel=0.03)
    K.box(1.72, 1.08, 0.2, base=True, parent=body, loc=(-0.35, 0, 0.98), color=c.accent, kind="gloss")
    K.box(0.78, 1.0, 0.95, base=True, parent=body, loc=(0.95, 0, 0.49), color=cab, kind="gloss", bevel=0.06)
    K.box(0.05, 0.86, 0.4, parent=body, loc=(1.345, 0, 1.15), color="#1d3557", kind="gloss")
    K.box(0.42, 1.02, 0.3, parent=body, loc=(1.0, 0, 1.15), color="#1d3557", kind="gloss")
    K.box(0.12, 1.02, 0.12, parent=body, loc=(1.36, 0, 0.55), color="#adb5bd", kind="metal")
    for y in (-0.36, 0.36):
        K.box(0.04, 0.16, 0.1, parent=body, loc=(1.36, y, 0.74), color="#fff3b0", kind="emit",
              emit=4 if c.night else 1)
    wheels = []
    for x in (-0.85, -0.3, 0.98):
        for y in (-0.48, 0.48):
            w = K.empty("wheel", parent=root, loc=(x, y, 0.26))
            K.cyl(0.26, 0.16, seg=16, parent=w, rot=(HALF, 0, 0), color="#212529")
            K.cyl(0.12, 0.18, seg=10, parent=w, rot=(HALF, 0, 0), color="#adb5bd", kind="metal")
            wheels.append(w)
    speed, mid = 1.1, c.t0 + (c.dur - c.t0) / 2
    K.animate(root, lambda t, s: s.loc.__setitem__(0, s.loc.x + speed * (t - mid)))
    for w in wheels:
        K.animate(w, lambda t, s: s.rot.__setitem__(1, s.rot.y + speed * (t - mid) / 0.26))
    K.animate(body, lambda t, s: s.loc.__setitem__(2, s.loc.z + 0.01 * math.sin(t * 15)))
    return Built(root, 1.75, 2.7)


def shopfront(c):
    root = K.empty("shopfront")
    wall = c.rng.choice(["#f4e9cd", "#ffd6a5", "#caf0f8", "#e9edc9", "#ffcad4"])
    K.box(2.5, 1.5, 2.3, base=True, parent=root, color=wall)
    K.box(2.62, 1.62, 0.12, base=True, parent=root, loc=(0, 0, 2.3), color="#6c757d")
    K.box(1.4, 0.08, 1.0, parent=root, loc=(-0.45, -0.73, 1.05), color="#343a40")
    K.box(1.3, 0.04, 0.9, parent=root, loc=(-0.45, -0.75, 1.05), color="#ffe8a3", kind="emit",
          emit=3.0 if c.night else 1.0)
    for z in (0.72, 1.08):
        K.box(1.3, 0.05, 0.03, parent=root, loc=(-0.45, -0.78, z), color="#8d6e63")
        x = -1.05
        while x < 0.12:
            w = c.rng.uniform(0.07, 0.13)
            K.box(w, 0.04, c.rng.uniform(0.12, 0.25), base=True, parent=root, loc=(x + w / 2, -0.8, z + 0.015),
                  color=c.rng.choice(PRODUCT_COLS), kind="gloss")
            x += w + 0.03
    K.box(0.6, 0.06, 1.4, base=True, parent=root, loc=(0.72, -0.75, 0), color="#6b4226")
    K.box(0.4, 0.03, 0.55, parent=root, loc=(0.72, -0.785, 0.98), color="#a2d2ff", kind="gloss")
    K.sphere(0.03, seg=8, rings=6, parent=root, loc=(0.52, -0.8, 0.7), color=GOLD, kind="metal")
    K.box(2.4, 0.1, 0.42, parent=root, loc=(0, -0.8, 2.02), color=c.accent, kind="emit",
          emit=2.5 if c.night else 0.6)
    K.cyl(0.15, 0.02, seg=24, parent=root, loc=(-0.85, -0.86, 2.02), rot=(HALF, 0, 0), color="#ffffff",
          kind="emit", emit=1.5)
    for k, w in enumerate((1.3, 0.9)):
        K.box(w, 0.02, 0.07, parent=root, loc=(-0.55 + w / 2, -0.86, 2.08 - k * 0.13), color="#ffffff",
              kind="emit", emit=1.5)
    a, b = c.rng.choice((("#e63946", "#f8f9fa"), ("#2a9d8f", "#f8f9fa"), ("#3a86ff", "#ffd166")))
    for i in range(8):
        x = -1.05 + i * 0.3
        K.box(0.3, 0.75, 0.035, parent=root, loc=(x, -1.05, 1.68), rot=(0.4, 0, 0), color=a if i % 2 else b)
        K.hemisphere(0.15, seg=12, rings=6, parent=root, loc=(x, -1.4, 1.53), rot=(PI, 0, 0),
                     scale=(1, 0.2, 0.55), color=a if i % 2 else b)
    for x in (-1.15, 1.15):
        K.cyl(0.16, 0.3, r2=0.2, seg=12, base=True, parent=root, loc=(x, -0.98, 0), color="#bc6c25")
        K.ico(0.24, sub=1, parent=root, loc=(x, -0.98, 0.48), scale=(1, 1, 1.2), color="#40916c")
    return Built(root, 2.6, 2.6)


def billboard(c):
    root = K.empty("billboard")
    for x in (-0.9, 0.9):
        K.cyl(0.07, 1.7, seg=10, base=True, parent=root, loc=(x, 0.1, 0), color="#6c757d", kind="metal")
    K.box(3.1, 0.14, 1.75, parent=root, loc=(0, 0.1, 2.45), color="#343a40", kind="gloss")
    poster = K.empty("poster", parent=root, loc=(0, 0.02, 2.45))
    K.box(2.95, 0.02, 1.6, parent=poster, color=c.accent, kind="emit", emit=1.0)
    parts = []
    parts.append(K.cyl(0.62, 0.02, seg=40, parent=poster, loc=(-0.75, -0.02, 0), rot=(HALF, 0, 0),
                       color="#ffffff", kind="emit", emit=1.1))
    bottle = K.empty("product", parent=poster, loc=(-0.75, -0.06, -0.12))
    K.cyl(0.17, 0.55, seg=20, base=True, parent=bottle, color="#e63946", kind="gloss")
    K.cyl(0.07, 0.16, seg=12, base=True, parent=bottle, loc=(0, 0, 0.55), color="#e63946", kind="gloss")
    K.box(0.35, 0.02, 0.18, parent=bottle, loc=(0, -0.17, 0.27), color="#ffffff")
    parts.append(bottle)
    for k, (w, z) in enumerate(((1.15, 0.45), (0.95, 0.2), (0.7, -0.05))):
        parts.append(K.box(w, 0.02, 0.13 if k == 0 else 0.09, parent=poster, loc=(0.2 + w / 2, -0.02, z),
                           color="#ffffff", kind="emit", emit=1.4))
    burst = K.prism(_star_points(12, 0.33, 0.24), depth=0.03, parent=poster, loc=(0.95, -0.04, -0.45),
                    color="#ffd60a", kind="emit", emit=2)
    K.spin(burst, speed=0.12, axis=1)
    parts.append(burst)
    for i, p in enumerate(parts):
        K.pop(p, delay=c.t0 + 0.2 + 0.15 * i, dur=0.5)
    for x in (-0.9, 0.9):
        K.segment((x, 0.1, 3.3), (x, -0.35, 3.55), r=0.02, parent=root, color="#6c757d", kind="metal")
        K.box(0.3, 0.12, 0.06, parent=root, loc=(x, -0.38, 3.55), color="#343a40")
        K.box(0.26, 0.1, 0.02, parent=root, loc=(x, -0.38, 3.52), color="#fff3c4", kind="emit", emit=6)
        if c.night:
            K.light("SPOT", 150, "#fff1d6", loc=(x, -0.45, 3.45), target=(x * 0.6, 0.0, 2.3), size=0.2,
                    shadow=False).parent = root
    return Built(root, 3.6, 3.1)


def whiteboard(c):
    root = K.empty("whiteboard")
    for x in (-0.82, 0.82):
        K.cyl(0.025, 2.0, seg=8, base=True, parent=root, loc=(x, 0.05, 0.05), color="#adb5bd", kind="metal")
        K.box(0.06, 0.6, 0.04, parent=root, loc=(x, 0.05, 0.06), color="#6c757d", kind="metal")
        for y in (-0.25, 0.35):
            K.sphere(0.05, seg=8, rings=6, parent=root, loc=(x, y, 0.04), color="#212529")
    K.box(1.9, 0.05, 1.15, parent=root, loc=(0, 0, 1.45), color="#adb5bd", kind="metal")
    K.box(1.82, 0.03, 1.07, parent=root, loc=(0, -0.025, 1.45), color="#ffffff", kind="gloss")
    K.box(1.4, 0.12, 0.03, parent=root, loc=(0, -0.08, 0.88), color="#adb5bd", kind="metal")
    for k, col in enumerate(("#e63946", "#1d3557")):
        K.cyl(0.015, 0.13, seg=8, parent=root, loc=(-0.2 + 0.2 * k, -0.1, 0.91), rot=(0, HALF, 0), color=col)
    ink = dict(parent=root, kind="emit", emit=0.6)
    K.box(0.012, 0.01, 0.82, base=True, loc=(-0.78, -0.045, 1.02), color="#212529", **ink)
    K.box(1.05, 0.01, 0.012, base=True, loc=(-0.26, -0.045, 1.02), color="#212529", **ink)
    pts = [Vector((-0.72, -0.05, 1.12)), Vector((-0.52, -0.05, 1.3)), Vector((-0.34, -0.05, 1.22)),
           Vector((-0.12, -0.05, 1.5)), Vector((0.08, -0.05, 1.58)), Vector((0.22, -0.05, 1.8))]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        seg = K.segment(a, b, r=0.014, color="#3a86ff", **ink)
        d0 = c.t0 + 0.3 + 0.22 * i
        K.animate(seg, lambda t, s, d0=d0: s.scale.__setitem__(2, s.scale.z * max(1e-4, K.clamp((t - d0) / 0.22))))
    for i, (z, col) in enumerate(((1.78, "#ffd166"), (1.45, "#ff8fab"), (1.12, "#80ed99"))):
        note = K.box(0.28, 0.012, 0.25, parent=root, loc=(0.6, -0.05, z), rot=(0, c.rng.uniform(-0.12, 0.12), 0),
                     color=col)
        for k in range(3):
            K.box(0.18 - 0.04 * k, 0.004, 0.015, parent=note, loc=(-0.02, -0.008, 0.06 - 0.06 * k),
                  color="#495057")
        K.pop(note, delay=c.t0 + 0.6 + 0.25 * i, dur=0.4)
    return Built(root, 2.1, 1.9)


def tv(c):
    root = K.empty("tv")
    K.box(1.7, 0.5, 0.5, base=True, parent=root, color="#8d5524", kind="gloss", bevel=0.02)
    K.box(0.32, 0.22, 0.06, base=True, parent=root, loc=(0, 0, 0.5), color="#212529", kind="gloss")
    K.box(0.06, 0.06, 0.12, base=True, parent=root, loc=(0, 0, 0.56), color="#212529")
    K.box(1.6, 0.07, 0.95, parent=root, loc=(0, 0, 1.15), color="#111111", kind="gloss", bevel=0.01)
    screen = K.empty("screen", parent=root, loc=(0, -0.04, 1.15))
    bg = K.box(1.5, 0.01, 0.85, parent=screen, color="#3a86ff", kind="emit", emit=1.4)
    palette = ["#3a86ff", "#ff006e", "#06d6a0", "#ff9f1c"]

    def recolor(t):
        k = t / 2.2
        i = int(k) % len(palette)
        f = K.smooth((k - int(k) - 0.8) / 0.2)
        col = K.mix(palette[i], palette[(i + 1) % len(palette)], f)
        bg.color = (*col, 1.4)
    K.every_frame(recolor)
    prod = K.empty("product", parent=screen, loc=(-0.4, -0.02, -0.3))
    K.box(0.3, 0.02, 0.44, base=True, parent=prod, color="#ffffff", kind="emit", emit=1.2)
    K.box(0.3, 0.025, 0.12, base=True, parent=prod, loc=(0, 0, 0.18), color="#ffd166", kind="emit", emit=1.5)
    K.animate(prod, lambda t, s: s.loc.__setitem__(2, s.loc.z + 0.04 * abs(math.sin(t * 3))))
    for k, w in enumerate((0.55, 0.42, 0.3)):
        K.box(w, 0.015, 0.06, parent=screen, loc=(0.05 + w / 2, -0.02, 0.22 - 0.12 * k), color="#ffffff",
              kind="emit", emit=1.5)
    burst = K.prism(_star_points(10, 0.16, 0.11), depth=0.015, parent=screen, loc=(0.5, -0.02, -0.22),
                    color="#ffd60a", kind="emit", emit=2)
    K.spin(burst, speed=0.2, axis=1)
    return Built(root, 1.7, 1.7)


def produce(c):
    root = K.empty("produce")
    fills = (("#fb8500", 0.085, (1, 1, 1)), ("#e63946", 0.08, (1, 1, 0.9)), ("#80b918", 0.09, (1, 1, 1)),
             ("#6a4c93", 0.07, (1, 1, 1.7)), ("#ffd60a", 0.06, (2.4, 0.7, 0.7)))
    crates = ((-0.6, 0.0, 0.0), (0.02, -0.05, 0.0), (0.64, 0.06, 0.0), (-0.28, 0.55, 0.0), (0.36, 0.55, 0.0))
    wood = "#c08552"
    for i, (x, y, z) in enumerate(crates):
        cr = K.empty("crate", parent=root, loc=(x, y, z), rot=(0, 0, c.rng.uniform(-0.1, 0.1)))
        K.box(0.56, 0.42, 0.04, base=True, parent=cr, color=wood)
        for zz in (0.06, 0.2):
            for sy in (-0.2, 0.2):
                K.box(0.56, 0.025, 0.1, base=True, parent=cr, loc=(0, sy, zz), color=wood)
            for sx in (-0.27, 0.27):
                K.box(0.025, 0.42, 0.1, base=True, parent=cr, loc=(sx, 0, zz), color=wood)
        col, r, sc = fills[i % len(fills)]
        for k in range(11):
            K.sphere(r, seg=10, rings=6, parent=cr,
                     loc=(c.rng.uniform(-0.2, 0.2), c.rng.uniform(-0.13, 0.13), 0.22 + c.rng.uniform(0, 0.1)),
                     scale=sc, rot=(0, 0, c.rng.uniform(0, PI)), color=col, kind="gloss")
        K.pop(cr, delay=c.t0 + 0.12 * i, dur=0.45)
        if i >= 3:
            cr.location.z = 0.32
            K.box(0.56, 0.42, 0.32, base=True, parent=root, loc=(x, y, 0), color=wood)
    return Built(root, 0.75, 1.9)


def down_chart(c):
    root = K.empty("down_chart")
    K.box(1.8, 0.6, 0.06, base=True, parent=root, color="#e9ecef", kind="gloss")
    cols = ["#f4a261", "#f08c5a", "#ee6c4d", "#e5383b", "#ba181b"]
    heights = (1.65, 1.3, 0.95, 0.62, 0.32)
    tops = []
    for i, h in enumerate(heights):
        x = -0.68 + i * 0.34
        bar = K.box(0.24, 0.3, h, base=True, parent=root, loc=(x, 0, 0.06), color=cols[i], kind="gloss",
                    bevel=0.02)
        d0 = c.t0 + 0.2 * i
        K.animate(bar, lambda t, s, d0=d0: s.scale.__setitem__(2, s.scale.z * max(1e-4, K.ease_out((t - d0) / 0.6))))
        tops.append(Vector((x, -0.3, 0.06 + h + 0.25)))
    arrow = K.empty("arrow", parent=root)
    for a, b in zip(tops, tops[1:]):
        K.segment(a, b, r=0.035, parent=arrow, color="#d00000", kind="emit", emit=2)
    tip = K.cone(0.1, 0.24, seg=10, parent=arrow, loc=tops[-1] + Vector((0.08, 0, -0.06)), color="#d00000",
                 kind="emit", emit=2)
    tip.rotation_euler = (tops[-1] - tops[-2]).to_track_quat("Z", "Y").to_euler()
    K.pop(arrow, delay=c.t0 + 1.2, dur=0.6)
    return Built(root, 2.0, 1.9)


def _wheel(parent, loc, r, spokes=8):
    w = K.empty("wheel", parent=parent, loc=loc)
    K.torus(r, 0.03, seg=24, rseg=6, parent=w, rot=(HALF, 0, 0), color="#212529")
    for i in range(spokes // 2):
        a = PI * i / (spokes // 2)
        K.segment((r * math.cos(a), 0, r * math.sin(a)), (-r * math.cos(a), 0, -r * math.sin(a)), r=0.007,
                  parent=w, color="#adb5bd", kind="metal")
    K.cyl(0.04, 0.08, seg=8, parent=w, rot=(HALF, 0, 0), color="#adb5bd", kind="metal")
    return w


def rickshaw(c):
    root = K.empty("rickshaw")
    body = K.empty("body", parent=root)
    hood_col = c.rng.choice(["#e63946", "#3a86ff", "#ff006e", "#06d6a0", "#8338ec"])
    frame = dict(parent=body, color="#2b2d42", kind="metal")
    r = 0.32
    wheels = [_wheel(root, (-0.45, y, r), r) for y in (-0.5, 0.5)] + [_wheel(root, (1.2, 0, r), r)]
    K.cyl(0.02, 1.0, seg=8, loc=(-0.45, 0, r), rot=(HALF, 0, 0), **frame)
    K.segment((-0.45, 0, r + 0.05), (0.75, 0, 0.62), r=0.025, **frame)
    K.segment((0.75, 0, 0.62), (1.2, 0, r), r=0.022, **frame)
    K.segment((0.75, 0, 0.62), (0.7, 0, 0.98), r=0.022, **frame)
    K.segment((1.2, 0, r), (1.12, 0, 1.12), r=0.022, **frame)
    K.cyl(0.018, 0.55, seg=8, loc=(1.12, 0, 1.12), rot=(HALF, 0, 0), **frame)
    K.box(0.26, 0.16, 0.06, parent=body, loc=(0.68, 0, 1.0), color="#212529", kind="gloss", bevel=0.02)
    K.box(0.65, 1.0, 0.32, base=True, parent=body, loc=(-0.4, 0, 0.42), color=K.shade(hood_col, 0.75),
          kind="gloss", bevel=0.02)
    K.box(0.58, 0.92, 0.12, base=True, parent=body, loc=(-0.38, 0, 0.74), color="#ffd60a")
    K.box(0.1, 0.92, 0.5, base=True, parent=body, loc=(-0.68, 0, 0.74), color="#ffd60a")
    K.box(0.42, 0.8, 0.04, parent=body, loc=(0.05, 0, 0.48), color="#6c757d", kind="metal")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.62)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4 or v.co.x > 1e-4], context="VERTS")
    K.mesh_object("hood", bm, parent=body, loc=(-0.38, 0, 0.88), color=hood_col, smooth=True)
    for i in range(9):
        a = PI * (i + 0.5) / 9
        K.cone(0.03, 0.09, seg=6, parent=body, loc=(-0.36, 0.62 * math.cos(a), 0.86 + 0.62 * math.sin(a)),
               rot=(PI, 0, 0), color=c.rng.choice(["#ffd60a", "#ff006e", "#06d6a0", "#ffffff"]))
    K.box(0.03, 0.9, 0.34, parent=body, loc=(-0.745, 0, 0.6), color="#ffffff")
    for k, col in enumerate(("#ff006e", "#ffd60a", "#3a86ff")):
        K.cyl(0.09, 0.02, seg=16, parent=body, loc=(-0.765, -0.28 + 0.28 * k, 0.6), rot=(0, HALF, 0), color=col)
    speed, mid = 0.7, c.t0 + (c.dur - c.t0) / 2
    K.animate(root, lambda t, s: s.loc.__setitem__(0, s.loc.x + speed * (t - mid)))
    for w in wheels:
        K.animate(w, lambda t, s: s.rot.__setitem__(1, s.rot.y + speed * (t - mid) / r))
    return Built(root, 1.6, 2.1)


def _registry():
    from factory import vocab
    missing = [n for n in vocab.PROPS if not callable(globals().get(n))]
    if missing:
        raise RuntimeError(f"props.py has no builder for: {missing}")
    return {n: globals()[n] for n in vocab.PROPS}


REGISTRY = _registry()
