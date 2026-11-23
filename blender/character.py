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


MALE_HAIR = ["short", "short", "side", "spiky", "curly"]
FEMALE_HAIR = ["long", "long", "bun", "ponytail", "hijab", "hijab"]
HIJABS = ["#1d3557", "#6d597a", "#2a9d8f", "#e5989b", "#f1faee", "#bc6c25", "#264653"]


def random_look(rng, kind=None):
    """A complete, repeatable look: the same seed always gives the same person."""
    kind = kind or rng.choice(["boy", "girl", "man", "woman"])
    female = kind in ("girl", "woman", "old_woman")
    adult = kind not in ("boy", "girl")
    look = {
        "type": kind,
        "skin": rng.choice(SKINS),
        "shirt": rng.choice(SHIRTS),
        "pants": rng.choice(PANTS),
        "hair": rng.choice(HAIRS),
        "hair_style": rng.choice(FEMALE_HAIR if female else MALE_HAIR),
        "hijab": rng.choice(HIJABS),
        "beard": rng.choice(["", "", "beard", "mustache"]) if adult and not female else "",
        "tupi": adult and not female and rng.random() < 0.12,
        "glasses": adult and rng.random() < 0.2,
        "build": rng.choice(["slim", "normal", "normal", "heavy"]) if adult else "normal",
        "height": round(rng.uniform(0.95, 1.05), 3),
    }
    if kind == "old_man" and not look["beard"]:
        look["beard"] = "beard"
    return look


def build(look, c, loc=(0, 0, 0), scale=1.0, astronaut=False, outfit=None):
    kind = look.get("type", "man")
    child = kind in ("boy", "girl")
    old = kind.startswith("old")
    female = kind in ("girl", "woman", "old_woman")
    robot = kind == "robot"
    s = scale * (0.74 if child else 1.0) * float(look.get("height", 1.0))
    wide = {"slim": 0.88, "heavy": 1.2}.get(look.get("build"), 1.0) if not robot else 1.0
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
    shoe = "#3d2b1f" if not robot else "#495057"
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
    elif outfit == "office":
        shirt = sleeve = "#cfe8fc" if not female else "#f8f9fa"
        pants = "#2b2d42"
    elif outfit == "chef":
        shirt = sleeve = "#f8f9fa"
        pants = "#343a40"
    elif outfit == "delivery":
        shirt = sleeve = "#e85d04"
        pants = "#212529"
    elif outfit == "police":
        shirt = sleeve = "#1d3557"
        pants = "#14213d"
        shoe = "#111111"
    elif outfit == "teacher":
        sleeve = "#f8f9fa"
        shirt = K.shade(shirt, 0.6)
    elif outfit == "traditional":
        if female:
            sleeve = shirt  # saree in the look's colour
        else:
            shirt = sleeve = K.shade(shirt, 1.8)  # light panjabi
            pants = "#f8f9fa"
    elif outfit == "sports":
        pants = "#1d3557"
        shoe = "#f8f9fa"
    bare_legs = (female and not robot and outfit != "traditional") or outfit == "sports"
    lower = shirt if female and outfit == "traditional" else (skin if bare_legs else pants)

    root = K.empty("char", loc=loc, scale=s)
    body = K.empty("body", parent=root)
    ch = {"root": root, "body": body, "hip": [], "knee": [], "sh": [], "el": [], "eyes": [],
          "height": 2.05 * s, "kind": kind, "skin": skin, "shirt": shirt}

    # legs
    for side in (-1, 1):
        hip = K.empty("hip", parent=body, loc=(side * 0.11, 0, 0.86))
        K.cyl(0.085, 0.45, seg=10, top=True, parent=hip, color=pants, kind=surf)
        knee = K.empty("knee", parent=hip, loc=(0, 0, -0.43))
        K.cyl(0.075, 0.4, seg=10, top=True, parent=knee, color=lower, kind=surf)
        K.box(0.14, 0.25, 0.09, parent=knee, loc=(0, -0.04, -0.41), color=shoe, kind="gloss", bevel=0.02)
        ch["hip"].append(hip)
        ch["knee"].append(knee)

    # torso
    if robot:
        K.box(0.52, 0.36, 0.62, base=True, parent=body, loc=(0, 0, 0.8), color=shirt, kind="metal",
              bevel=0.04)
        K.box(0.2, 0.02, 0.14, parent=body, loc=(0, -0.19, 1.15), color="#4cc9f0", kind="emit", emit=3)
    elif female:
        K.cyl(0.36, 0.5, r2=0.21, seg=14, base=True, parent=body, loc=(0, 0, 0.66), color=shirt,
              scale=(wide, wide, 1))
        K.cyl(0.21, 0.3, r2=0.24, seg=14, base=True, parent=body, loc=(0, 0, 1.12), color=shirt,
              scale=(wide, wide, 1))
    else:
        K.cyl(0.215, 0.14, seg=14, base=True, parent=body, loc=(0, 0, 0.8), color=pants, scale=(wide, wide, 1))
        K.cyl(0.21, 0.5, r2=0.25, seg=14, base=True, parent=body, loc=(0, 0, 0.93), color=shirt,
              scale=(wide, wide, 1))
    if astronaut:
        K.box(0.4, 0.22, 0.5, base=True, parent=body, loc=(0, 0.3, 0.9), color="#adb5bd", kind="gloss",
              bevel=0.04)
        K.box(0.14, 0.02, 0.1, parent=body, loc=(0.08, -0.26, 1.2), color="#e63946", kind="emit", emit=2)
    K.cyl(0.075, 0.12, seg=10, base=True, parent=body, loc=(0, 0, 1.4), color=skin, kind=surf)

    # arms
    for side in (-1, 1):
        sh = K.empty("shoulder", parent=body, loc=(side * 0.3 * (1 + (wide - 1) * 0.8), 0, 1.36),
                     rot=(0, -side * 0.1, 0))
        K.sphere(0.085, seg=10, rings=6, parent=sh, color=sleeve, kind=surf)
        K.cyl(0.068, 0.34, seg=10, top=True, parent=sh, color=sleeve, kind=surf)
        el = K.empty("elbow", parent=sh, loc=(0, 0, -0.32))
        long_sleeve = robot or astronaut or outfit in ("suit", "doctor", "chef", "police", "office",
                                                       "traditional", "teacher")
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
        ch["mouth"] = K.box(0.2, 0.02, 0.04, parent=head, loc=(0, -0.215, 0.13), color="#4cc9f0", kind="emit",
                            emit=3)
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
        # mouth: a smile line plus a dark opening that moves when the character speaks
        K.torus(0.055, 0.012, seg=12, rseg=5, arc=0.5, parent=head, loc=(0, -0.245, 0.16),
                rot=(math.pi / 2, math.pi, 0), color="#7a2e2e")
        ch["mouth"] = K.sphere(0.05, seg=12, rings=6, parent=head, loc=(0, -0.236, 0.146),
                               scale=(1.2, 0.35, 0.08), color="#4a1414")
        for x in (-0.15, 0.15):
            K.sphere(0.04, seg=8, rings=5, parent=head, loc=(x, -0.205, 0.17), scale=(1, 0.4, 0.7),
                     color="#ff8fa3")
        _hair(ch, head, look, hair, female, old, kind, outfit)
        if old or (look.get("glasses") and not astronaut):
            _glasses(head, "#495057" if old else "#212529")
    if astronaut:
        K.sphere(0.4, seg=24, rings=14, parent=head, loc=(0, 0, 0.24), color="#caf0f8", kind="glass")
        K.torus(0.24, 0.05, seg=20, rseg=6, parent=head, loc=(0, 0, -0.04), color="#adb5bd", kind="metal")
    _dress_up(ch, outfit, female, look, c, old)
    ch["outfit"] = outfit
    return ch


HATS = {"farmer", "worker", "chef", "police", "delivery"}


def _hair(ch, head, look, hair, female, old, kind, outfit="casual"):
    """Hair style, hijab, beard / moustache and tupi."""
    style = look.get("hair_style") or ("long" if female else "short")
    hat = outfit in HATS
    if female and style == "hijab":
        col = look.get("hijab", "#1d3557")
        K.hemisphere(0.33, seg=20, rings=10, parent=head, loc=(0, -0.12, 0.25), rot=(-math.pi / 2, 0, 0),
                     scale=(1, 1, 1.25), color=col)
        K.hemisphere(0.285, seg=20, rings=8, parent=head, loc=(0, 0.0, 0.3), scale=(1.03, 1.03, 0.85), color=col)
        K.cyl(0.36, 0.32, r2=0.2, seg=18, base=True, parent=ch["body"], loc=(0, 0.02, 1.28), color=col)
        return
    if old and not female:  # bald on top, hair on the sides and back
        K.sphere(0.27, seg=16, rings=10, parent=head, loc=(0, 0.07, 0.22), scale=(1.02, 0.9, 0.9), color=hair)
    elif style == "curly" and not hat:
        K.sphere(0.27, seg=16, rings=10, parent=head, loc=(0, 0.06, 0.24), scale=(1, 0.9, 1), color=hair)
        for i in range(14):
            a = K.TAU * i / 9
            ring = 0 if i < 9 else 1
            r = (0.2, 0.1)[ring]
            K.sphere(0.075, seg=8, rings=5, parent=head, color=hair,
                     loc=(r * math.cos(a + ring), 0.02 + r * math.sin(a + ring), (0.42, 0.5)[ring]))
    else:
        K.hemisphere(0.275, parent=head, loc=(0, 0.02, 0.33), scale=(1, 1.02, 0.8), color=hair)
        K.sphere(0.27, seg=16, rings=10, parent=head, loc=(0, 0.06, 0.24), scale=(1, 0.9, 1), color=hair)
        if not female and not hat:
            if style == "side":
                K.sphere(0.13, seg=12, rings=6, parent=head, loc=(0.1, -0.13, 0.45), scale=(1.5, 0.8, 0.45),
                         color=hair)
            elif style == "spiky":
                for i in range(6):
                    a = K.TAU * i / 6
                    K.cone(0.05, 0.12, seg=6, parent=head, loc=(0.1 * math.cos(a), 0.1 * math.sin(a), 0.55),
                           rot=(0.5 * math.sin(a), -0.5 * math.cos(a), 0), color=hair)
    if female:
        if style in ("long",) or old:
            K.sphere(0.3, seg=16, rings=10, parent=head, loc=(0, 0.12, 0.02), scale=(1, 0.6, 1.5), color=hair)
        if style == "bun" or old:
            K.sphere(0.12, seg=12, rings=8, parent=head, loc=(0, 0.17, 0.46), color=hair)
        if style == "ponytail":
            K.sphere(0.09, seg=10, rings=6, parent=head, loc=(0, 0.27, 0.32), color=hair)
            K.sphere(0.08, seg=10, rings=6, parent=head, loc=(0, 0.31, 0.12), scale=(0.75, 0.75, 1.9), color=hair)
    beard = look.get("beard", "")
    if beard and not female:
        col = "#dcdcdc" if old else hair
        if beard == "beard":
            K.hemisphere(0.255, seg=16, rings=8, parent=head, loc=(0, -0.02, 0.11), rot=(math.pi, 0, 0),
                         scale=(1.02, 1.0, 0.62), color=col)
        K.sphere(0.05, seg=10, rings=6, parent=head, loc=(0, -0.252, 0.188), scale=(1.35, 0.45, 0.35), color=col)
    if look.get("tupi") and not female and not hat:
        K.hemisphere(0.215, seg=16, rings=6, parent=head, loc=(0, 0.02, 0.475), scale=(1, 1, 0.55), color="#f8f9fa")


def speak(ch, level):
    """Move the mouth with the voice. level(t) -> 0..1 (how open)."""
    mouth, head = ch.get("mouth"), ch["head"]
    if mouth is None:
        return
    def move(t, s):
        k = level(t)
        s.scale.z *= 1 + 9.0 * k
        s.loc.z -= 0.012 * k  # the jaw drops a little
    K.animate(mouth, move)
    K.animate(head, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.05 * level(t)))


def chatter(ch, phase=0.0):
    """Mouth moving in a talking rhythm (for people we see talking but don't hear)."""
    def level(t):
        syll = max(0.0, math.sin(K.TAU * 3.1 * t + phase)) * (0.6 + 0.4 * K.wobble(t, phase, 2.0))
        breath = K.smooth((math.sin(K.TAU * 0.27 * t + phase) + 0.6) / 0.4)  # short pauses between phrases
        return max(0.0, syll) * breath * 0.8
    speak(ch, level)


def _glasses(head, color="#212529"):
    for x in (-0.09, 0.09):
        K.torus(0.058, 0.011, seg=16, rseg=5, parent=head, loc=(x, -0.255, 0.27), rot=(math.pi / 2, 0, 0),
                color=color, kind="gloss")
    K.box(0.06, 0.012, 0.012, parent=head, loc=(0, -0.26, 0.28), color=color)


def _dress_up(ch, outfit, female, look, c, old=False):
    """Outfit accessories: they make the actor's job and situation readable at a glance."""
    body, head = ch["body"], ch["head"]
    front = -0.26 if female else -0.245  # chest surface (toward the camera)
    if outfit == "office":
        K.box(0.17, 0.03, 0.08, parent=body, loc=(0, -0.22, 1.38), color="#ffffff")
        if not female:
            K.box(0.06, 0.02, 0.3, parent=body, loc=(0, -0.245, 1.18), color="#1d3557", kind="gloss")
            K.box(0.075, 0.025, 0.055, parent=body, loc=(0, -0.245, 1.33), color="#14213d", kind="gloss")
        K.torus(0.15, 0.008, seg=16, rseg=4, parent=body, loc=(0, -0.06, 1.3), rot=(0.8, 0, 0), color="#3a86ff")
        cx = 0.1 if not female else 0.0
        K.box(0.085, 0.012, 0.11, parent=body, loc=(cx, front - 0.01, 1.08), color="#ffffff")
        K.box(0.085, 0.014, 0.03, parent=body, loc=(cx, front - 0.012, 1.12), color="#3a86ff")
        return
    if outfit == "chef":
        K.cyl(0.2, 0.26, r2=0.22, seg=16, base=True, parent=head, loc=(0, 0, 0.4), color="#f8f9fa")
        K.sphere(0.25, seg=16, rings=8, parent=head, loc=(0, 0, 0.72), scale=(1, 1, 0.55), color="#f8f9fa")
        K.torus(0.11, 0.035, seg=16, rseg=6, parent=body, loc=(0, -0.02, 1.4), color="#e63946")
        for x in (-0.07, 0.07):
            for z in (1.02, 1.14, 1.26):
                K.sphere(0.018, seg=6, rings=4, parent=body, loc=(x, front - 0.005, z), color="#495057")
        return
    if outfit == "delivery":
        K.hemisphere(0.285, seg=16, rings=8, parent=head, loc=(0, 0.01, 0.36), scale=(1, 1, 0.75), color="#e85d04")
        K.cyl(0.17, 0.02, seg=16, parent=head, loc=(0, -0.25, 0.37), scale=(1, 0.85, 1), color="#9d0208")
        K.box(0.5, 0.36, 0.5, parent=body, loc=(0, 0.42, 1.12), color="#e85d04", kind="gloss", bevel=0.03)
        K.box(0.51, 0.37, 0.08, parent=body, loc=(0, 0.42, 1.22), color="#ffffff")
        for x in (-0.13, 0.13):
            K.box(0.05, 0.02, 0.26, parent=body, loc=(x, front + 0.03, 1.27), color="#9d0208")
        return
    if outfit == "police":
        K.cyl(0.27, 0.1, seg=18, base=True, parent=head, loc=(0, 0, 0.4), color="#14213d")
        K.cyl(0.31, 0.07, r2=0.33, seg=18, base=True, parent=head, loc=(0, 0.02, 0.5), color="#1d3557")
        K.cyl(0.17, 0.02, seg=16, parent=head, loc=(0, -0.24, 0.42), scale=(1, 0.75, 1), color="#111111",
              kind="gloss")
        K.cyl(0.04, 0.02, seg=12, parent=head, loc=(0, -0.3, 0.53), rot=(math.pi / 2, 0, 0), color="#ffd166",
              kind="metal")
        if not female:
            K.cyl(0.225, 0.07, seg=16, base=True, parent=body, loc=(0, 0, 0.9), color="#111111", kind="gloss")
            K.box(0.07, 0.02, 0.05, parent=body, loc=(0, -0.23, 0.935), color="#ffd166", kind="metal")
        K.cyl(0.035, 0.015, seg=10, parent=body, loc=(0.1, front - 0.005, 1.24), rot=(math.pi / 2, 0, 0),
              color="#ffd166", kind="metal")
        for x in (-0.27, 0.27):
            K.box(0.14, 0.12, 0.025, parent=body, loc=(x, 0, 1.44), color="#14213d")
        return
    if outfit == "teacher":
        if not old and not look.get("glasses"):
            _glasses(head)
        K.box(0.17, 0.03, 0.08, parent=body, loc=(0, -0.22, 1.38), color="#ffffff")
        if not female:
            K.box(0.05, 0.02, 0.12, parent=body, loc=(0, -0.25, 1.3), color="#9d0208")
        K.cyl(0.01, 0.08, seg=6, parent=body, loc=(0.1, front - 0.005, 1.25), color="#3a86ff")
        return
    if outfit == "traditional":
        col = look["shirt"]
        if female:  # saree: long skirt with a gold border, pallu over the shoulder
            K.cyl(0.29, 0.66, r2=0.33, seg=18, base=True, parent=body, loc=(0, 0, 0.02), color=col)
            K.cyl(0.295, 0.06, seg=18, base=True, parent=body, loc=(0, 0, 0.06), color="#ffd166", kind="metal")
            K.box(0.13, 0.02, 0.62, parent=body, loc=(0.05, -0.27, 1.1), rot=(0, -0.55, 0), color=col)
            K.box(0.025, 0.022, 0.62, parent=body, loc=(0.11, -0.275, 1.11), rot=(0, -0.55, 0), color="#ffd166",
                  kind="metal")
            K.box(0.16, 0.02, 0.6, parent=body, loc=(0.16, 0.24, 1.12), color=col)
        else:  # panjabi: long tunic to the knees
            K.cyl(0.255, 0.56, r2=0.225, seg=16, base=True, parent=body, loc=(0, 0, 0.42), color=ch.get("shirt", col))
            for z in (1.14, 1.24, 1.34):
                K.sphere(0.016, seg=6, rings=4, parent=body, loc=(0, -0.248, z), color="#d4a373", kind="metal")
            K.cyl(0.085, 0.05, seg=12, base=True, parent=body, loc=(0, 0, 1.4), color=ch.get("shirt", col))
        return
    if outfit == "sports":
        K.torus(0.255, 0.03, seg=20, rseg=6, parent=head, loc=(0, 0, 0.36), rot=(0.12, 0, 0), color="#ffffff")
        K.cyl(0.08, 0.01, seg=16, parent=body, loc=(0, front - 0.005, 1.2), rot=(math.pi / 2, 0, 0), color="#ffffff")
        K.box(0.03, 0.012, 0.09, parent=body, loc=(-0.02, front - 0.012, 1.2), color="#212529")
        K.box(0.03, 0.012, 0.09, parent=body, loc=(0.025, front - 0.012, 1.2), color="#212529")
        return
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


WALKING = ("walk", "run", "carry", "push_cart")
HEAD_BUSY = ("read", "sad", "think", "work", "point", "listen", "phone", "write", "drink", "search", "announce")


def act(ch, action, c, phase=0.0, facing=0.0, travel=True, seated=False, mode=None, hand=0, voice=None):
    """Attach an action loop. Returns a function t -> world offset of the character (for camera tracking).

    seated: sit down while doing a hand action (tea at a bench, typing at a desk)
    mode:   "type" makes "work" type on a keyboard (default: from the shot's props)
    hand:   0 or 1, the arm used for one-handed actions (the arm nearest the camera)
    voice:  level(t) -> 0..1 from the narration: this character says the line (lip-sync)
    """
    if voice is not None:
        speak(ch, voice)
    elif action in ("talk", "announce"):
        chatter(ch, phase)
    sin, TAU = math.sin, K.TAU
    body, head = ch["body"], ch["head"]
    sh, el, hip, knee = ch["sh"], ch["el"], ch["hip"], ch["knee"]
    root = ch["root"]
    root.rotation_euler.z = facing
    offset = lambda t: Vector((0, 0, 0))  # noqa: E731
    work_mode = mode if mode is not None else getattr(c, "work_mode", "")
    h, o = hand, 1 - hand          # main hand / other hand
    side = (-1, 1)[h]

    for i, e in enumerate(ch["eyes"]):
        _blink(e, phase)
    K.animate(body, lambda t, s: s.scale.__setitem__(2, s.scale.z * (1 + 0.012 * sin(TAU * 0.3 * t + phase))))

    if action not in HEAD_BUSY:
        K.animate(head, lambda t, s: s.rot.__setitem__(2, s.rot.z + 0.25 * K.wobble(t, phase + 1, 0.25)))

    def pose(joint, x=0.0, y=0.0, z=0.0):
        """Hold a joint at a fixed offset from its rest pose."""
        def f(t, s):
            s.rot.x += x
            s.rot.y += y
            s.rot.z += z
        K.animate(joint, f)

    if action in WALKING:
        run = action == "run"
        carry = action == "carry"
        push = action == "push_cart"
        f = 1.5 if run else (0.85 if carry or push else 0.95)
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
            elif push:  # both hands on the cart handle
                pose(sh[i], x=-0.95, y=-side * 0.05)
                pose(el[i], x=-0.45)
            else:
                K.animate(sh[i], arm)
                K.animate(el[i], lambda t, s: s.rot.__setitem__(0, s.rot.x - (1.3 if run else 0.35)))
        if carry:
            box = K.empty("parcel", parent=body, loc=(0, -0.5, 1.0))
            K.box(0.5, 0.4, 0.36, parent=box, color="#c8a165", bevel=0.015)
            K.box(0.51, 0.08, 0.37, parent=box, color="#e9d8a6")
        if push:
            import props
            cart = props.shopping_cart(c)
            cart.root.parent = root
            cart.root.location = (0, -1.24, 0)
            cart.root.rotation_euler = (0, 0, -math.pi / 2)

        def bounce(t, s):
            s.loc.z += (0.06 if run else 0.035) * abs(sin(TAU * f * t))
            if run:
                s.rot.x += 0.2
        K.animate(body, bounce)
        if travel:
            speed = 2.2 if run else (0.85 if carry or push else 1.0)
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
        if work_mode == "type":
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

    elif action == "listen":  # hands together in front, nodding
        for i, sd in enumerate((-1, 1)):
            pose(sh[i], x=-0.28, y=sd * 0.28)
            pose(el[i], x=-1.05)

        def nod(t, s):
            s.rot.x += 0.06 + 0.1 * max(0.0, sin(TAU * 0.7 * t + phase))
            s.rot.y += 0.12
        K.animate(head, nod)
        K.sway(body, 0.025, 0.3, 1, phase)

    elif action == "phone":
        pose(sh[h], x=-0.45, y=side * 0.3)
        pose(el[h], x=-1.75)
        ph = K.empty("phone", parent=el[h], loc=(0, -0.06, -0.36))
        K.box(0.1, 0.014, 0.18, parent=ph, color="#212529", kind="gloss", bevel=0.01)
        K.box(0.085, 0.004, 0.155, parent=ph, loc=(0, -0.009, 0), color="#4cc9f0", kind="emit", emit=2.5)
        K.animate(ph, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.06 * sin(TAU * 0.5 * t)))
        pose(head, x=0.3, y=-side * 0.05)
        K.sway(sh[o], 0.04, 0.3, 0, phase)

    elif action == "buy":  # hold out money, shopping bag in the other hand
        def offer(t, s):
            s.rot.x += -1.2 - 0.06 * sin(TAU * 0.6 * t + phase)
            s.rot.y += side * 0.08
        K.animate(sh[h], offer)
        pose(el[h], x=-0.3)
        cash = K.empty("cash", parent=el[h], loc=(0, -0.05, -0.38))
        for k, col in enumerate(("#52b788", "#74c69d", "#40916c")):
            K.box(0.17, 0.008, 0.085, parent=cash, loc=(0, -0.006 * k, 0), rot=(0, 0.25 * (k - 1), 0), color=col)
        pose(sh[o], x=-0.08, y=side * 0.15)
        bag = K.empty("bag", parent=el[o], loc=(0, 0, -0.36))
        K.box(0.26, 0.12, 0.3, parent=bag, loc=(0, 0, -0.2), color=c.accent)
        K.torus(0.06, 0.01, seg=12, rseg=4, arc=0.5, parent=bag, loc=(0, 0, -0.05), rot=(math.pi / 2, 0, 0),
                color=K.shade(c.accent, 0.6))

    elif action == "give":  # hold a product out with both hands
        for i, sd in enumerate((-1, 1)):
            def hold(t, s, sd=sd):
                s.rot.x += -1.0 - 0.07 * sin(TAU * 0.5 * t + phase)
                s.rot.y += sd * 0.3
            K.animate(sh[i], hold)
            pose(el[i], x=-0.55)
        item = K.empty("product", parent=body, loc=(0, -0.6, 1.08))
        K.animate(item, lambda t, s: s.loc.__setitem__(1, s.loc.y - 0.05 * sin(TAU * 0.5 * t + phase)))
        K.box(0.34, 0.24, 0.26, parent=item, color=c.accent, kind="gloss", bevel=0.02)
        K.box(0.345, 0.245, 0.06, parent=item, loc=(0, 0, 0.04), color="#ffffff")
        pose(body, x=0.05)

    elif action == "shake_hands":
        def shake(t, s):
            s.rot.x += -0.95 - 0.12 * sin(TAU * 1.6 * t + phase)
            s.rot.y += side * 0.12
        K.animate(sh[h], shake)
        pose(el[h], x=-0.45)
        pose(body, x=0.05)
        K.sway(sh[o], 0.04, 0.3, 0, phase)

    elif action == "write":  # clipboard in one hand, pen in the other
        pose(sh[o], x=-0.65, y=-side * 0.35)
        pose(el[o], x=-1.15)
        board = K.empty("clipboard", parent=body, loc=(-side * 0.04, -0.42, 1.1), rot=(-0.55, 0, 0))
        K.box(0.3, 0.38, 0.015, parent=board, color="#a47148")
        K.box(0.26, 0.32, 0.004, parent=board, loc=(0, 0.01, 0.009), color="#ffffff")
        for k in range(4):
            K.box(0.18, 0.012, 0.003, parent=board, loc=(-0.02, -0.08 + 0.06 * k, 0.012), color="#495057")
        K.box(0.12, 0.04, 0.03, parent=board, loc=(0, -0.17, 0.015), color="#adb5bd", kind="metal")

        def scribble(t, s):
            s.rot.x += -0.75 + 0.05 * sin(TAU * 2.2 * t)
            s.rot.y += side * 0.3 + 0.04 * sin(TAU * 1.1 * t)
        K.animate(sh[h], scribble)
        pose(el[h], x=-1.25)
        K.cyl(0.012, 0.14, seg=6, parent=el[h], loc=(0, -0.04, -0.38), rot=(0.6, 0, 0), color="#1d3557")
        pose(head, x=0.38)

    elif action == "announce":  # megaphone at the mouth, other fist pumping
        pose(sh[h], x=-1.3, z=-side * 0.45)
        pose(el[h], x=-1.45)
        mega = K.empty("megaphone", parent=body, loc=(0, -0.5, 1.68), rot=(-0.12, 0, 0))
        K.cyl(0.2, 0.45, r2=0.06, seg=16, parent=mega, rot=(-math.pi / 2, 0, 0), color=c.accent, kind="gloss")
        K.torus(0.2, 0.02, seg=20, rseg=5, parent=mega, loc=(0, -0.225, 0), rot=(math.pi / 2, 0, 0),
                color="#343a40", kind="gloss")
        for i in range(3):
            ring = K.torus(0.22, 0.018, seg=24, rseg=5, parent=mega, loc=(0, -0.3, 0), rot=(math.pi / 2, 0, 0),
                           color=c.accent, kind="emit", emit=3)

            def wave_out(t, s, ph=i / 3):
                u = (t * 0.9 + ph) % 1.0
                s.loc.y -= u * 0.9
                s.scale *= max(1e-4, (0.7 + 1.2 * u) * (1 - u ** 3))
            K.animate(ring, wave_out)
        K.animate(sh[o], lambda t, s: s.rot.__setitem__(1, s.rot.y + side * (2.2 + 0.2 * sin(TAU * 1.4 * t))))
        pose(el[o], y=side * 0.3)
        K.animate(body, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.06 + 0.03 * sin(TAU * 1.4 * t)))

    elif action == "thumbs_up":
        pose(sh[h], x=-1.05, y=side * 0.1)
        pose(el[h], x=-1.35)
        K.cyl(0.026, 0.11, seg=8, parent=el[h], loc=(0, -0.02, -0.42), color=ch["skin"])
        K.animate(head, lambda t, s: s.rot.__setitem__(0, s.rot.x + 0.05 * sin(TAU * 0.9 * t)))
        K.animate(body, lambda t, s: s.loc.__setitem__(2, s.loc.z + 0.015 * abs(sin(TAU * 0.9 * t))))
        K.sway(sh[o], 0.04, 0.3, 0, phase)

    elif action == "clap":
        for i, sd in enumerate((-1, 1)):
            def clap(t, s, sd=sd):
                u = 0.5 + 0.5 * sin(TAU * 2.0 * t + phase)
                s.rot.x += -1.0
                s.rot.y += sd * (0.5 - 0.32 * u)
            K.animate(sh[i], clap)
            pose(el[i], x=-0.95)
        K.animate(body, lambda t, s: s.loc.__setitem__(2, s.loc.z + 0.012 * abs(sin(TAU * 2.0 * t + phase))))

    elif action == "shrug":
        def up(t):
            return K.smooth(0.5 + 0.9 * sin(TAU * 0.4 * t + phase))
        for i, sd in enumerate((-1, 1)):
            def arm_up(t, s, sd=sd):
                k = up(t)
                s.loc.z += 0.05 * k
                s.rot.x += -0.25 - 0.15 * k
                s.rot.y += -sd * (0.3 + 0.2 * k)
            K.animate(sh[i], arm_up)

            def fore(t, s, sd=sd):
                k = up(t)
                s.rot.x += -1.1 - 0.2 * k
                s.rot.y += -sd * 0.5 * k
            K.animate(el[i], fore)
        K.animate(head, lambda t, s: (s.rot.__setitem__(1, s.rot.y + 0.18 * up(t)),
                                      s.rot.__setitem__(0, s.rot.x - 0.06 * up(t))))

    elif action == "drink":  # tea cup to the mouth now and then
        def lift(t):
            u = (t * 0.3 + phase * 0.1) % 1.0
            return K.smooth((u - 0.5) / 0.12) * (1 - K.smooth((u - 0.82) / 0.12))
        K.animate(sh[h], lambda t, s: (s.rot.__setitem__(0, s.rot.x - 0.35 - 0.5 * lift(t)),
                                       s.rot.__setitem__(1, s.rot.y + side * (0.35 - 0.15 * lift(t)))))
        K.animate(el[h], lambda t, s: s.rot.__setitem__(0, s.rot.x - 1.6 - 0.55 * lift(t)))
        cup = K.empty("cup", parent=el[h], loc=(0, -0.06, -0.38))
        K.animate(cup, lambda t, s: s.rot.__setitem__(0, s.rot.x + 1.95 + 0.6 * lift(t)))
        K.cyl(0.045, 0.09, r2=0.055, seg=12, base=True, parent=cup, color="#f8f9fa", kind="gloss")
        K.cyl(0.05, 0.005, seg=12, base=True, parent=cup, loc=(0, 0, 0.08), color="#8d5524")
        K.torus(0.025, 0.008, seg=10, rseg=4, parent=cup, loc=(0.055, 0, 0.045), rot=(math.pi / 2, 0, 0),
                color="#f8f9fa")
        K.animate(head, lambda t, s: s.rot.__setitem__(0, s.rot.x - 0.12 * lift(t)))
        pose(sh[o], x=-0.4, y=-side * 0.3)
        pose(el[o], x=-1.25)

    elif action == "search":  # hand over the eyes, looking left and right
        # a raised arm swings in around the vertical axis (rot y would push it outwards)
        pose(sh[h], x=-2.0, z=-side * 0.55)
        pose(el[h], x=-1.1)
        K.animate(head, lambda t, s: (s.rot.__setitem__(2, s.rot.z + 0.55 * sin(TAU * 0.22 * t + phase)),
                                      s.rot.__setitem__(0, s.rot.x - 0.08)))
        K.animate(body, lambda t, s: s.rot.__setitem__(2, s.rot.z + 0.15 * sin(TAU * 0.22 * t + phase)))
        K.sway(sh[o], 0.04, 0.3, 0, phase)

    else:  # idle
        for i in range(2):
            K.sway(sh[i], 0.05, 0.3, 0, phase + i)
        K.sway(body, 0.03, 0.2, 1, phase)

    if seated and action not in WALKING + ("sit", "celebrate"):
        K.animate(body, lambda t, s: s.loc.__setitem__(2, s.loc.z - 0.41))
        for i in range(2):
            pose(hip[i], x=-1.55)
            pose(knee[i], x=1.55)
    return offset
