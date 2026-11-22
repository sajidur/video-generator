"""Stylised low-poly character with jointed limbs and a set of actions.

The character faces -Y (towards the default camera). Joint rotation signs:
  hip/shoulder rot X < 0  -> limb swings forward
  knee rot X > 0          -> lower leg bends back
  shoulder rot Y = -side*a -> arm raises sideways (side = -1 left, +1 right)
  head rot X > 0          -> looks down
"""
import math

from mathutils import Matrix, Vector

import kit as K

SKINS = ["#f1c27d", "#e0ac69", "#c68642", "#8d5524", "#ffdbac"]
SHIRTS = ["#e63946", "#2a9d8f", "#457b9d", "#f4a261", "#8338ec", "#ff006e", "#3a86ff", "#06d6a0"]
PANTS = ["#264653", "#1d3557", "#3d405b", "#5c4033", "#2b2d42"]
HAIRS = ["#2b1d0e", "#4a2c17", "#0f0f0f", "#6b4423", "#a0522d"]


def random_look(rng, kind=None):
    return {
        "type": kind or rng.choice(["boy", "girl", "man", "woman"]),
        "skin": rng.choice(SKINS),
        "shirt": rng.choice(SHIRTS),
        "pants": rng.choice(PANTS),
        "hair": rng.choice(HAIRS),
    }


def build(look, c, loc=(0, 0, 0), scale=1.0, astronaut=False, outfit=None):
    kind = look.get("type", "man")
    child = kind in ("boy", "girl")
    old = kind.startswith("old")
    female = kind in ("girl", "woman", "old_woman")
    robot = kind == "robot"
    s = scale * (0.74 if child else 1.0)
    skin, shirt, pants = look["skin"], look["shirt"], look["pants"]
    hair = "#dcdcdc" if old else look["hair"]
    surf = "matte"
    outfit = outfit or look.get("outfit") or "casual"
    if robot:
        skin, shirt, pants, surf = "#adb5bd", "#ced4da", "#6c757d", "metal"
        outfit = "casual"
    if astronaut:
        shirt, pants = "#f1f3f5", "#dee2e6"
        outfit = "casual"
    sleeve = shirt
    if outfit == "poor":
        shirt = sleeve = K.mix(shirt, "#8a8174", 0.65)
        pants = "#6b5b4a"
    elif outfit == "suit":
        shirt = sleeve = pants = "#22304a"
    elif outfit == "doctor":
        sleeve = "#f8f9fa"
        if female:
            shirt = "#f8f9fa"
    elif outfit == "worker":
        shirt = "#fb8500"

    root = K.empty("char", loc=loc, scale=s)
    body = K.empty("body", parent=root)
    ch = {"root": root, "body": body, "hip": [], "knee": [], "sh": [], "el": [], "eyes": [],
          "height": 2.05 * s, "kind": kind, "skin": skin}

    # legs
    for side in (-1, 1):
        hip = K.empty("hip", parent=body, loc=(side * 0.11, 0, 0.86))
        K.cyl(0.085, 0.45, seg=10, top=True, parent=hip, color=pants, kind=surf)
        knee = K.empty("knee", parent=hip, loc=(0, 0, -0.43))
        K.cyl(0.075, 0.4, seg=10, top=True, parent=knee, color=skin if female and not robot else pants,
              kind=surf)
        K.box(0.14, 0.25, 0.09, parent=knee, loc=(0, -0.04, -0.41), color="#3d2b1f" if not robot else "#495057",
              kind="gloss", bevel=0.02)
        ch["hip"].append(hip)
        ch["knee"].append(knee)

    # torso
    if robot:
        K.box(0.52, 0.36, 0.62, base=True, parent=body, loc=(0, 0, 0.8), color=shirt, kind="metal",
              bevel=0.04)
        K.box(0.2, 0.02, 0.14, parent=body, loc=(0, -0.19, 1.15), color="#4cc9f0", kind="emit", emit=3)
    elif female:
        K.cyl(0.36, 0.5, r2=0.21, seg=14, base=True, parent=body, loc=(0, 0, 0.66), color=shirt)
        K.cyl(0.21, 0.3, r2=0.24, seg=14, base=True, parent=body, loc=(0, 0, 1.12), color=shirt)
    else:
        K.cyl(0.215, 0.14, seg=14, base=True, parent=body, loc=(0, 0, 0.8), color=pants)
        K.cyl(0.21, 0.5, r2=0.25, seg=14, base=True, parent=body, loc=(0, 0, 0.93), color=shirt)
    if astronaut:
        K.box(0.4, 0.22, 0.5, base=True, parent=body, loc=(0, 0.3, 0.9), color="#adb5bd", kind="gloss",
              bevel=0.04)
        K.box(0.14, 0.02, 0.1, parent=body, loc=(0.08, -0.26, 1.2), color="#e63946", kind="emit", emit=2)
    K.cyl(0.075, 0.12, seg=10, base=True, parent=body, loc=(0, 0, 1.4), color=skin, kind=surf)

    # arms
    for side in (-1, 1):
        sh = K.empty("shoulder", parent=body, loc=(side * 0.3, 0, 1.36), rot=(0, -side * 0.1, 0))
        K.sphere(0.085, seg=10, rings=6, parent=sh, color=sleeve, kind=surf)
        K.cyl(0.068, 0.34, seg=10, top=True, parent=sh, color=sleeve, kind=surf)
        el = K.empty("elbow", parent=sh, loc=(0, 0, -0.32))
        long_sleeve = robot or astronaut or outfit in ("suit", "doctor")
        K.cyl(0.058, 0.3, seg=10, top=True, parent=el, color=sleeve if long_sleeve else skin,
              kind=surf)
        K.sphere(0.078, seg=10, rings=6, parent=el, loc=(0, 0, -0.32),
                 color="#f8f9fa" if astronaut else skin, kind=surf)
        ch["sh"].append(sh)
        ch["el"].append(el)

    # head
    head = K.empty("head", parent=body, loc=(0, 0, 1.5))
    ch["head"] = head
    if robot:
        K.box(0.46, 0.42, 0.4, parent=head, loc=(0, 0, 0.24), color=skin, kind="metal", bevel=0.05)
        for x in (-0.1, 0.1):
            e = K.box(0.1, 0.02, 0.07, parent=head, loc=(x, -0.215, 0.28), color="#4cc9f0", kind="emit",
                      emit=6)
            ch["eyes"].append(e)
        K.box(0.2, 0.02, 0.04, parent=head, loc=(0, -0.215, 0.13), color="#4cc9f0", kind="emit", emit=3)
        K.cyl(0.015, 0.18, seg=6, base=True, parent=head, loc=(0, 0, 0.44), color="#6c757d")
        tip = K.sphere(0.04, seg=8, rings=6, parent=head, loc=(0, 0, 0.63), color="#ff006e", kind="emit",
                       emit=6)
        K.pulse(tip, 0.4, 1.5)
    else:
        K.sphere(0.26, seg=20, rings=12, parent=head, loc=(0, 0, 0.24), color=skin)
        for x in (-0.09, 0.09):
            e = K.sphere(0.04, seg=10, rings=6, parent=head, loc=(x, -0.225, 0.27), scale=(1, 0.6, 1.25),
                         color="#1b1b1b", kind="gloss")
            K.sphere(0.012, seg=6, rings=4, parent=e, loc=(0.012, -0.03, 0.015), color="#ffffff",
                     kind="emit", emit=2)
            ch["eyes"].append(e)
        if not (old and not female):
            K.torus(0.055, 0.012, seg=12, rseg=5, arc=0.5, parent=head, loc=(0, -0.245, 0.16),
                    rot=(math.pi / 2, math.pi, 0), color="#7a2e2e")
        for x in (-0.15, 0.15):
            K.sphere(0.04, seg=8, rings=5, parent=head, loc=(x, -0.205, 0.17), scale=(1, 0.4, 0.7),
                     color="#ff8fa3")
        if old and not female:
            K.sphere(0.2, seg=12, rings=8, parent=head, loc=(0, -0.16, 0.06), scale=(1, 0.7, 0.9),
                     color=hair)
            K.sphere(0.27, seg=16, rings=10, parent=head, loc=(0, 0.07, 0.22), scale=(1.02, 0.9, 0.9),
                     color=hair)
        else:
            K.hemisphere(0.275, parent=head, loc=(0, 0.02, 0.33), scale=(1, 1.02, 0.8), color=hair)
            K.sphere(0.27, seg=16, rings=10, parent=head, loc=(0, 0.06, 0.24), scale=(1, 0.9, 1), color=hair)
        if female:
            K.sphere(0.3, seg=16, rings=10, parent=head, loc=(0, 0.12, 0.02), scale=(1, 0.6, 1.5), color=hair)
            if old:
                K.sphere(0.12, seg=12, rings=8, parent=head, loc=(0, 0.12, 0.52), color=hair)
        if old:
            for x in (-0.09, 0.09):
                K.torus(0.058, 0.01, seg=16, rseg=5, parent=head, loc=(x, -0.255, 0.27),
                        rot=(math.pi / 2, 0, 0), color="#495057", kind="metal")
    if astronaut:
        K.sphere(0.4, seg=24, rings=14, parent=head, loc=(0, 0, 0.24), color="#caf0f8", kind="glass")
        K.torus(0.24, 0.05, seg=20, rseg=6, parent=head, loc=(0, 0, -0.04), color="#adb5bd", kind="metal")
    _dress_up(ch, outfit, female, look, c)
    ch["outfit"] = outfit
    return ch


def _dress_up(ch, outfit, female, look, c):
    """Outfit accessories: they make the actor's job and situation readable at a glance."""
    body, head = ch["body"], ch["head"]
    if outfit == "poor":
        K.box(0.11, 0.02, 0.11, parent=body, loc=(0.08, -0.245, 1.05), rot=(0, 0.3, 0), color="#8d6e63")
        K.box(0.09, 0.02, 0.09, parent=ch["hip"][0], loc=(0, -0.09, -0.22), color="#a1887f")
    elif outfit == "suit":
        K.box(0.17, 0.03, 0.1, parent=body, loc=(0, -0.225, 1.37), color="#f8f9fa")
        if not female:
            K.box(0.065, 0.02, 0.32, parent=body, loc=(0, -0.245, 1.17), color="#c1121f", kind="gloss")
            K.box(0.08, 0.025, 0.06, parent=body, loc=(0, -0.245, 1.33), color="#9d0208", kind="gloss")
    elif outfit == "farmer":
        K.cyl(0.44, 0.03, seg=20, parent=head, loc=(0, 0, 0.45), color="#e0b86a")
        K.cyl(0.2, 0.17, r2=0.16, seg=16, base=True, parent=head, loc=(0, 0, 0.46), color="#d4a373")
        K.cyl(0.205, 0.04, seg=16, base=True, parent=head, loc=(0, 0, 0.47), color="#9c6644")
        if not female:  # lungi
            K.cyl(0.27, 0.6, r2=0.24, seg=16, base=True, parent=body, loc=(0, 0, 0.3), color="#1d6f8a")
            K.cyl(0.275, 0.05, seg=16, base=True, parent=body, loc=(0, 0, 0.42), color="#f1faee")
    elif outfit == "shopkeeper":
        if female:
            K.box(0.34, 0.02, 0.55, parent=body, loc=(0, -0.3, 0.92), rot=(-0.29, 0, 0), color="#f1e3c8")
        else:
            K.box(0.38, 0.025, 0.64, parent=body, loc=(0, -0.24, 0.95), color="#f1e3c8")
            K.box(0.16, 0.012, 0.1, parent=body, loc=(0, -0.255, 0.86), color="#d4a373")
        K.box(0.2, 0.02, 0.04, parent=body, loc=(0, -0.2, 1.38), color="#f1e3c8")
    elif outfit == "doctor":
        if not female:
            K.cyl(0.285, 0.92, r2=0.262, seg=16, base=True, parent=body, loc=(0, 0, 0.5), color="#f8f9fa")
            K.box(0.11, 0.02, 0.3, parent=body, loc=(0, -0.27, 1.26), color=look["shirt"])
        K.torus(0.17, 0.014, seg=20, rseg=5, parent=body, loc=(0, -0.03, 1.36), rot=(0.35, 0, 0),
                color="#343a40")
        K.cyl(0.04, 0.02, seg=10, parent=body, loc=(0.07, -0.28, 1.1), rot=(math.pi / 2, 0, 0),
              color="#adb5bd", kind="metal")
    elif outfit == "student":
        K.box(0.38, 0.2, 0.46, parent=body, loc=(0, 0.3, 1.08), color=c.accent, kind="gloss", bevel=0.04)
        K.box(0.3, 0.05, 0.16, parent=body, loc=(0, 0.42, 0.98), color=K.shade(c.accent, 0.7))
        for x in (-0.13, 0.13):
            K.box(0.05, 0.02, 0.26, parent=body, loc=(x, -0.215, 1.27), color=K.shade(c.accent, 0.7))
    elif outfit == "worker":
        for z in ((1.2, 1.32) if female else (1.02, 1.22)):
            K.cyl(0.262, 0.04, seg=16, base=True, parent=body, loc=(0, 0, z), color="#e9ecef")
        K.hemisphere(0.3, parent=head, loc=(0, 0, 0.4), color="#ffd60a", kind="gloss")
        K.cyl(0.34, 0.025, seg=20, parent=head, loc=(0, 0, 0.41), color="#ffc300", kind="gloss")


def _blink(eye, phase):
    def f(t, s):
        if (t + phase) % 3.7 < 0.12:
            s.scale.z *= 0.12
    K.animate(eye, f)


def act(ch, action, c, phase=0.0, facing=0.0, travel=True):
    """Attach an action loop. Returns a function t -> world offset of the character (for camera tracking)."""
    sin, TAU = math.sin, K.TAU
    body, head = ch["body"], ch["head"]
    sh, el, hip, knee = ch["sh"], ch["el"], ch["hip"], ch["knee"]
    root = ch["root"]
    root.rotation_euler.z = facing
    offset = lambda t: Vector((0, 0, 0))  # noqa: E731

    for i, e in enumerate(ch["eyes"]):
        _blink(e, phase)
    K.animate(body, lambda t, s: s.scale.__setitem__(2, s.scale.z * (1 + 0.012 * sin(TAU * 0.3 * t + phase))))

    if action not in ("read", "sad", "think", "work", "point"):
        K.animate(head, lambda t, s: s.rot.__setitem__(2, s.rot.z + 0.25 * K.wobble(t, phase + 1, 0.25)))

    def pose(joint, x=0.0, y=0.0, z=0.0):
        """Hold a joint at a fixed offset from its rest pose."""
        def f(t, s):
            s.rot.x += x
            s.rot.y += y
            s.rot.z += z
        K.animate(joint, f)

    if action in ("walk", "run", "carry"):
        run = action == "run"
        carry = action == "carry"
        f = 1.5 if run else (0.85 if carry else 0.95)
        a_hip, a_knee, a_arm = (0.75, 1.3, 0.9) if run else (0.42, 0.65, 0.45)
        for i, side in enumerate((-1, 1)):
            ph = 0 if side < 0 else math.pi

            def leg(t, s, ph=ph):
                s.rot.x += -a_hip * sin(TAU * f * t + ph)

            def kn(t, s, ph=ph):
                s.rot.x += a_knee * max(0.0, sin(TAU * f * t + ph + 1.2))

            def arm(t, s, ph=ph):
                s.rot.x += a_arm * sin(TAU * f * t + ph)

            K.animate(hip[i], leg)
            K.animate(knee[i], kn)
            if carry:  # both arms hold the box in front
                pose(sh[i], x=-0.8, y=side * 0.18)
                pose(el[i], x=-0.75)
            else:
                K.animate(sh[i], arm)
                K.animate(el[i], lambda t, s: s.rot.__setitem__(0, s.rot.x - (1.3 if run else 0.35)))
        if carry:
            box = K.empty("parcel", parent=body, loc=(0, -0.5, 1.0))
            K.box(0.5, 0.4, 0.36, parent=box, color="#c8a165", bevel=0.015)
            K.box(0.51, 0.08, 0.37, parent=box, color="#e9d8a6")

        def bounce(t, s):
            s.loc.z += (0.06 if run else 0.035) * abs(sin(TAU * f * t))
            if run:
                s.rot.x += 0.2
        K.animate(body, bounce)
        if travel:
            speed = 2.2 if run else (0.85 if carry else 1.0)
            mid = c.t0 + (c.dur - c.t0) / 2
            fwd = Matrix.Rotation(facing, 3, "Z") @ Vector((0, -1, 0))

            def go(t, s):
                s.loc += fwd * speed * (t - mid)
            K.animate(root, go)
            offset = lambda t: fwd * speed * (t - mid)  # noqa: E731

    elif action == "talk":
        for i, side in enumerate((-1, 1)):
            ph = i * 1.7

            def gesture(t, s, ph=ph, side=side):
                s.rot.x += -0.35 - 0.12 * sin(TAU * 0.7 * t + ph)
                s.rot.y += -side * (0.22 + 0.1 * sin(TAU * 0.6 * t + ph))

            K.animate(sh[i], gesture)
            K.animate(el[i], lambda t, s, ph=ph: s.rot.__setitem__(0, s.rot.x - 1.05 - 0.35 * sin(TAU * 0.9 * t + ph)))
        K.animate(head, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.06 * sin(TAU * 1.1 * t)))
        K.sway(body, 0.04, 0.4, 2, phase)

    elif action == "point":
        K.animate(sh[1], lambda t, s: (s.rot.__setitem__(1, s.rot.y - 1.45),
                                       s.rot.__setitem__(0, s.rot.x - 0.35 - 0.06 * sin(TAU * 0.8 * t))))
        pose(el[1], y=-0.1)
        K.cyl(0.022, 0.12, seg=6, top=True, parent=el[1], loc=(0, 0, -0.36), color=ch["skin"])
        K.sway(sh[0], 0.05, 0.3, 0, phase)
        pose(head, z=0.3)

    elif action == "work":
        if getattr(c, "work_mode", "") == "type":
            for i in range(2):
                pose(sh[i], x=-0.75)
                K.animate(el[i], lambda t, s, i=i: s.rot.__setitem__(0, s.rot.x - 0.85 - 0.08 * sin(TAU * 5 * t + i * math.pi)))
            pose(head, x=0.22)
        else:  # hammering on a crate
            def strike(t, s):
                u = (t * 1.3 + phase) % 1.0
                lift = K.smooth(u / 0.7) if u < 0.7 else 1 - K.smooth((u - 0.7) / 0.12)
                s.rot.x += -0.55 - 1.7 * lift
            K.animate(sh[1], strike)
            pose(el[1], x=-0.6)
            hammer = K.empty("hammer", parent=el[1], loc=(0, 0, -0.34), rot=(math.pi / 2, 0, 0))
            K.cyl(0.02, 0.34, seg=6, base=True, parent=hammer, color="#7f5539")
            K.box(0.16, 0.06, 0.06, parent=hammer, loc=(0, 0, 0.34), color="#495057", kind="metal")
            pose(sh[0], x=-0.7, y=0.15)
            pose(el[0], x=-0.6)
            pose(body, x=0.12)
            pose(head, x=0.25)
            K.box(0.6, 0.45, 0.5, base=True, parent=ch["root"], loc=(0, -0.72, 0), color="#a47148", bevel=0.02)

    elif action == "sit":
        K.box(0.44, 0.42, 0.45, base=True, parent=ch["root"], loc=(0, 0.06, 0), color="#8d6e63", bevel=0.02)
        K.animate(body, lambda t, s: s.loc.__setitem__(2, s.loc.z - 0.41))
        for i in range(2):
            pose(hip[i], x=-1.55)
            pose(knee[i], x=1.55)
            pose(sh[i], x=-0.45)
            pose(el[i], x=-0.75)

    elif action == "wave":
        K.animate(sh[1], lambda t, s: s.rot.__setitem__(1, s.rot.y - 2.45))
        K.animate(el[1], lambda t, s: s.rot.__setitem__(1, s.rot.y - 0.45 * sin(TAU * 1.8 * t)))
        K.sway(body, 0.04, 0.5, 1, phase)
        K.sway(sh[0], 0.05, 0.3, 0, phase)

    elif action == "celebrate":
        for i, side in enumerate((-1, 1)):
            def up(t, s, side=side):
                s.rot.y += -side * (2.55 + 0.15 * sin(TAU * 1.6 * t))
            K.animate(sh[i], up)
            K.animate(el[i], lambda t, s, side=side: s.rot.__setitem__(1, s.rot.y - side * 0.3))

        def jump(t, s):
            s.loc.z += 0.22 * abs(sin(math.pi * 1.6 * (t + phase)))
        K.animate(body, jump)
        for i in range(2):
            K.animate(knee[i], lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.35 * (1 - abs(sin(math.pi * 1.6 * (t + phase))))))

    elif action == "think":
        K.animate(sh[1], lambda t, s: (s.rot.__setitem__(0, s.rot.x - 1.0), s.rot.__setitem__(1, s.rot.y + 0.55)))
        K.animate(el[1], lambda t, s: s.rot.__setitem__(0, s.rot.x - 1.95))
        K.animate(sh[0], lambda t, s: (s.rot.__setitem__(0, s.rot.x - 0.5), s.rot.__setitem__(1, s.rot.y - 0.35)))
        K.animate(el[0], lambda t, s: s.rot.__setitem__(0, s.rot.x - 1.35))
        K.animate(head, lambda t, s: (s.rot.__setitem__(1, s.rot.y + 0.14),
                                      s.rot.__setitem__(0, s.rot.x - 0.12 + 0.05 * sin(TAU * 0.3 * t))))

    elif action == "read":
        for i, side in enumerate((-1, 1)):
            K.animate(sh[i], lambda t, s, side=side: (s.rot.__setitem__(0, s.rot.x - 0.45),
                                                     s.rot.__setitem__(1, s.rot.y + side * 0.32)))
            K.animate(el[i], lambda t, s: s.rot.__setitem__(0, s.rot.x - 1.25))
        K.animate(head, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.32 + 0.04 * sin(TAU * 0.25 * t)))
        bk = K.empty("book", parent=body, loc=(0, -0.44, 1.1), rot=(0.5, 0, 0))
        for side in (-1, 1):
            K.box(0.24, 0.32, 0.02, parent=bk, loc=(side * 0.12, 0, 0), rot=(0, side * 0.2, 0),
                  color=c.accent, kind="gloss")
            K.box(0.22, 0.29, 0.02, parent=bk, loc=(side * 0.115, 0, 0.018), rot=(0, side * 0.2, 0),
                  color="#fdfcdc")

    elif action == "sad":
        K.animate(head, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.45))
        K.animate(body, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.1))
        for i, side in enumerate((-1, 1)):
            K.animate(sh[i], lambda t, s, side=side: s.rot.__setitem__(1, s.rot.y + side * 0.06))

    else:  # idle
        for i in range(2):
            K.sway(sh[i], 0.05, 0.3, 0, phase + i)
        K.sway(body, 0.03, 0.2, 1, phase)
    return offset
