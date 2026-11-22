"""Low-level helpers for building stylised low-poly 3D scenes in Blender.

Runs inside Blender's Python. Everything animated is a pure function of time
(seconds), so any frame can be rendered independently (this is what makes
interrupted renders resumable).
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

TAU = math.tau

# --------------------------------------------------------------------------
# colours
# --------------------------------------------------------------------------


def lin(c):
    """'#rrggbb' (sRGB) or an (r,g,b) tuple (already linear) -> linear RGB tuple."""
    if isinstance(c, str):
        h = c.lstrip("#")
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb)
    return tuple(c[:3])


def mix(a, b, f):
    a, b = lin(a), lin(b)
    return tuple(a[i] + (b[i] - a[i]) * f for i in range(3))


def shade(c, f):
    """f < 1 darkens, f > 1 lightens (towards white)."""
    c = lin(c)
    if f <= 1:
        return tuple(x * f for x in c)
    return mix(c, (1, 1, 1), min(1, f - 1))


# --------------------------------------------------------------------------
# easing / maths
# --------------------------------------------------------------------------


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    x = clamp(x)
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def wobble(t, seed=0.0, speed=0.4):
    """Smooth noise in [-1, 1]."""
    return noise.noise(Vector((t * speed, seed * 7.13, 0.5)))


# --------------------------------------------------------------------------
# scene state
# --------------------------------------------------------------------------

FOG = {"color": (0.7, 0.8, 0.9), "start": 25.0, "end": 140.0, "amount": 0.0}
_MATS = {}
_MOTIONS = {}
_CALLBACKS = []


def reset():
    """Remove everything so the next shot starts from an empty scene."""
    _MATS.clear()
    _MOTIONS.clear()
    _CALLBACKS.clear()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves, bpy.data.worlds, bpy.data.textures, bpy.data.node_groups):
        for block in list(coll):
            try:
                coll.remove(block)
            except Exception:
                pass
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "_factory_frame":
            bpy.app.handlers.frame_change_pre.remove(h)


def scene():
    return bpy.context.scene


def link(ob):
    scene().collection.objects.link(ob)
    return ob


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------


def _add_fog(m, nt, shader_out, out_node):
    """Blend the surface towards the horizon colour with distance (aerial perspective)."""
    if FOG["amount"] <= 0:
        nt.links.new(shader_out, out_node.inputs["Surface"])
        return
    cam = nt.nodes.new("ShaderNodeCameraData")
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = FOG["start"]
    rng.inputs["From Max"].default_value = FOG["end"]
    rng.inputs["To Min"].default_value = 0.0
    rng.inputs["To Max"].default_value = FOG["amount"]
    rng.clamp = True
    nt.links.new(cam.outputs["View Distance"], rng.inputs["Value"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*FOG["color"], 1)
    em.inputs["Strength"].default_value = 1.0
    mixs = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(rng.outputs["Result"], mixs.inputs[0])
    nt.links.new(shader_out, mixs.inputs[1])
    nt.links.new(em.outputs["Emission"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], out_node.inputs["Surface"])


def _new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    return m, nt, bsdf, out


def shared(kind="matte"):
    """One material per surface kind; the colour comes from each object's colour.

    kinds: matte, gloss, metal, emit, glass, water
    For 'emit' the object's colour alpha is the emission strength.
    """
    if kind in _MATS:
        return _MATS[kind]
    m, nt, bsdf, out = _new_material("k_" + kind)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    nt.links.new(info.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = {"matte": 0.75, "gloss": 0.28, "metal": 0.3,
                                              "emit": 0.5, "glass": 0.05, "water": 0.12}[kind]
    if kind == "metal":
        bsdf.inputs["Metallic"].default_value = 1.0
    if kind == "emit":
        nt.links.new(info.outputs["Color"], bsdf.inputs["Emission Color"])
        nt.links.new(info.outputs["Alpha"], bsdf.inputs["Emission Strength"])
    if kind == "glass":
        bsdf.inputs["Alpha"].default_value = 0.22
        bsdf.inputs["Specular IOR Level"].default_value = 1.0
        m.surface_render_method = "BLENDED"
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    elif kind == "emit":
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    else:
        _add_fog(m, nt, bsdf.outputs["BSDF"], out)
    _MATS[kind] = m
    return m


def custom_material(name, build):
    """build(nt, bsdf) wires a custom node graph; fog is added automatically."""
    key = "custom:" + name
    if key in _MATS:
        return _MATS[key]
    m, nt, bsdf, out = _new_material(name)
    build(nt, bsdf)
    _add_fog(m, nt, bsdf.outputs["BSDF"], out)
    _MATS[key] = m
    return m


def two_tone_material(name, c1, c2, scale=0.15, rough=0.9):
    """Ground-style material: two colours blended by noise."""
    def build(nt, bsdf):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.4
        ramp.color_ramp.elements[0].color = (*lin(c1), 1)
        ramp.color_ramp.elements[1].position = 0.62
        ramp.color_ramp.elements[1].color = (*lin(c2), 1)
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = rough
    return custom_material(name, build)


# --------------------------------------------------------------------------
# objects
# --------------------------------------------------------------------------


def _finish(name, data, color, kind, emit, parent, loc, rot, scale, material=None):
    ob = link(bpy.data.objects.new(name, data))
    data.materials.append(material or shared(kind))
    c = lin(color)
    ob.color = (*c, emit if kind == "emit" else 1.0)
    if parent is not None:
        ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    return ob


def mesh_object(name, bm, color="#cccccc", kind="matte", emit=0.0, parent=None, loc=(0, 0, 0),
                rot=(0, 0, 0), scale=1.0, smooth=False, bevel=0.0, material=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = _finish(name, me, color, kind, emit, parent, loc, rot, scale, material)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return ob


def empty(name="pivot", parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    ob = link(bpy.data.objects.new(name, None))
    if parent is not None:
        ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    return ob


def box(sx=1.0, sy=1.0, sz=1.0, base=False, **kw):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z = v.co.z * sz + (sz / 2 if base else 0)
    return mesh_object(kw.pop("name", "box"), bm, **kw)


def cyl(r=0.5, h=1.0, seg=16, r2=None, base=False, top=False, **kw):
    """Cylinder along Z. base=True: sits on z=0. top=True: hangs below z=0."""
    bm = bmesh.new()
    off = h / 2 if base else (-h / 2 if top else 0.0)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=h,
                          matrix=Matrix.Translation((0, 0, off)))
    return mesh_object(kw.pop("name", "cyl"), bm, **kw)


def cone(r=0.5, h=1.0, seg=16, **kw):
    return cyl(r=r, h=h, seg=seg, r2=0.0, **kw)


def sphere(r=0.5, seg=16, rings=10, **kw):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    kw.setdefault("smooth", True)
    return mesh_object(kw.pop("name", "sphere"), bm, **kw)


def hemisphere(r=0.5, seg=16, rings=10, cut=0.0, **kw):
    """Sphere with everything below z=cut*r removed (caps, domes, hair)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut * r - 1e-4], context="VERTS")
    kw.setdefault("smooth", True)
    return mesh_object(kw.pop("name", "dome"), bm, **kw)


def ico(r=0.5, sub=1, jitter=0.0, rng=None, **kw):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    if jitter and rng:
        for v in bm.verts:
            v.co *= 1 + rng.uniform(-jitter, jitter)
    return mesh_object(kw.pop("name", "ico"), bm, **kw)


def torus(R=1.0, r=0.2, seg=32, rseg=10, arc=1.0, **kw):
    """Torus in the XY plane. arc<1 makes an open ring (e.g. a padlock shackle)."""
    bm = bmesh.new()
    closed = arc >= 0.999
    n = seg if closed else seg + 1
    rows = []
    for i in range(n):
        a = TAU * arc * i / seg
        row = []
        for j in range(rseg):
            b = TAU * j / rseg
            row.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a),
                                     (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        rows.append(row)
    for i in range(seg if closed else n - 1):
        i2 = (i + 1) % n
        for j in range(rseg):
            j2 = (j + 1) % rseg
            bm.faces.new((rows[i][j], rows[i2][j], rows[i2][j2], rows[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    kw.setdefault("smooth", True)
    return mesh_object(kw.pop("name", "torus"), bm, **kw)


def prism(points, depth=0.3, **kw):
    """Extrude a 2D outline drawn in the XZ plane (x right, z up) along Y.

    Front face points to -Y, i.e. towards the default camera.
    """
    bm = bmesh.new()
    verts = [bm.verts.new((x, -depth / 2, z)) for x, z in points]
    face = bm.faces.new(verts)
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, depth, 0), verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(kw.pop("name", "prism"), bm, **kw)


def grid(size=10.0, res=20, height=None, **kw):
    """Flat grid from -size..size; height(x, y) displaces vertices."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=res, size=size)
    if height:
        for v in bm.verts:
            v.co.z = height(v.co.x, v.co.y)
    return mesh_object(kw.pop("name", "grid"), bm, **kw)


def segment(p1, p2, r=0.05, seg=8, **kw):
    """Cylinder between two points."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    ob = cyl(r=r, h=d.length, seg=seg, **kw)
    ob.location = (p1 + p2) / 2
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return ob


_FONTS = {}


def font(path):
    if not path:
        return None
    if path not in _FONTS:
        try:
            _FONTS[path] = bpy.data.fonts.load(path, check_existing=True)
        except Exception:
            _FONTS[path] = None
    return _FONTS[path]


def text3d(body, size=0.5, depth=0.08, color="#ffffff", kind="gloss", emit=0.0, fontfile=None,
           parent=None, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), scale=1.0):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    cu.extrude = depth
    cu.bevel_depth = min(0.02, depth * 0.4)
    cu.bevel_resolution = 2
    cu.space_line = 0.85
    f = font(fontfile)
    if f:
        cu.font = f
    return _finish("txt", cu, color, kind, emit, parent, loc, rot, scale)


def light(kind="POINT", energy=100.0, color="#ffffff", loc=(0, 0, 3), rot=(0, 0, 0), size=0.5,
          shadow=True, target=None):
    data = bpy.data.lights.new("light", kind)
    data.energy = energy
    data.color = lin(color)
    data.use_shadow = shadow
    if kind == "SUN":
        data.angle = size
    elif kind == "AREA":
        data.size = size
    else:
        data.shadow_soft_size = size
    try:
        data.shadow_maximum_resolution = 0.02
    except Exception:
        pass
    ob = link(bpy.data.objects.new("light", data))
    ob.location = loc
    ob.rotation_euler = rot
    if target is not None:
        look_at(ob, target)
    return ob


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# --------------------------------------------------------------------------
# animation (stateless: everything is f(t))
# --------------------------------------------------------------------------


class _State:
    __slots__ = ("loc", "rot", "scale")


class _Motion:
    def __init__(self, ob):
        self.ob = ob
        self.fns = []
        self.base = None


def animate(ob, fn):
    """fn(t, state) adjusts state.loc / state.rot / state.scale (start = rest pose)."""
    m = _MOTIONS.get(ob.name)
    if m is None:
        m = _MOTIONS[ob.name] = _Motion(ob)
    m.fns.append(fn)
    return ob


def every_frame(fn):
    """fn(t) for anything else (lights, camera, mesh edits)."""
    _CALLBACKS.append(fn)
    return fn


def apply(t):
    for m in _MOTIONS.values():
        ob = m.ob
        if m.base is None:
            m.base = (ob.location.copy(), Vector(ob.rotation_euler), ob.scale.copy())
        st = _State()
        st.loc = m.base[0].copy()
        st.rot = m.base[1].copy()
        st.scale = m.base[2].copy()
        for fn in m.fns:
            fn(t, st)
        ob.location = st.loc
        ob.rotation_euler = st.rot
        ob.scale = st.scale
    for fn in _CALLBACKS:
        fn(t)


def pop(ob, delay=0.0, dur=0.6):
    def f(t, s):
        x = (t - delay) / dur
        k = 0.0 if x <= 0 else ease_out_back(x) if x < 1 else 1.0
        s.scale *= max(k, 1e-4)
    return animate(ob, f)


def bob(ob, amp=0.08, speed=0.5, phase=0.0):
    return animate(ob, lambda t, s: s.loc.__setitem__(2, s.loc.z + amp * math.sin(TAU * speed * t + phase)))


def spin(ob, speed=0.1, axis=2):
    def f(t, s):
        s.rot[axis] += TAU * speed * t
    return animate(ob, f)


def sway(ob, amp=0.05, speed=0.4, axis=1, phase=0.0):
    def f(t, s):
        s.rot[axis] += amp * math.sin(TAU * speed * t + phase)
    return animate(ob, f)


def pulse(ob, amp=0.06, speed=1.0, phase=0.0):
    def f(t, s):
        s.scale *= 1 + amp * math.sin(TAU * speed * t + phase)
    return animate(ob, f)


def drift(ob, vel=(0.3, 0, 0)):
    v = Vector(vel)

    def f(t, s):
        s.loc += v * t
    return animate(ob, f)


def flicker(ob, amp=0.15, speed=3.0, seed=0.0):
    def f(t, s):
        k = 1 + amp * noise.noise(Vector((t * speed, seed, 0.0)))
        s.scale.z *= k
        s.scale.x *= 1 + (k - 1) * 0.4
        s.scale.y *= 1 + (k - 1) * 0.4
    return animate(ob, f)


# --------------------------------------------------------------------------
# world / render
# --------------------------------------------------------------------------


def world_gradient(zenith, horizon, strength=1.0, stars=0.0, ground=None):
    w = bpy.data.worlds.new("world")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = -0.02
    rng.inputs["From Max"].default_value = 0.6
    nt.links.new(sep.outputs["Z"], rng.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].color = (*lin(horizon), 1)
    ramp.color_ramp.elements[1].color = (*lin(zenith), 1)
    nt.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
    color_out = ramp.outputs["Color"]
    if ground:
        below = nt.nodes.new("ShaderNodeMath")
        below.operation = "LESS_THAN"
        below.inputs[1].default_value = -0.02
        nt.links.new(sep.outputs["Z"], below.inputs[0])
        gmix = nt.nodes.new("ShaderNodeMix")
        gmix.data_type = "RGBA"
        nt.links.new(below.outputs[0], gmix.inputs["Factor"])
        nt.links.new(color_out, gmix.inputs["A"])
        gmix.inputs["B"].default_value = (*lin(ground), 1)
        color_out = gmix.outputs["Result"]
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(color_out, bg.inputs["Color"])
    shader = bg.outputs["Background"]
    if stars > 0:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 260.0
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        dot = nt.nodes.new("ShaderNodeMapRange")
        dot.inputs["From Min"].default_value = 0.0
        dot.inputs["From Max"].default_value = 0.06
        dot.inputs["To Min"].default_value = 1.0
        dot.inputs["To Max"].default_value = 0.0
        nt.links.new(vor.outputs["Distance"], dot.inputs["Value"])
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 6.0
        nt.links.new(dot.outputs["Result"], pw.inputs[0])
        rnd = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(vor.outputs["Color"], rnd.inputs["Color"])
        bright = nt.nodes.new("ShaderNodeMath")
        bright.operation = "MULTIPLY"
        nt.links.new(pw.outputs[0], bright.inputs[0])
        nt.links.new(rnd.outputs[0], bright.inputs[1])
        amt = nt.nodes.new("ShaderNodeMath")
        amt.operation = "MULTIPLY"
        amt.inputs[1].default_value = stars * 12.0
        nt.links.new(bright.outputs[0], amt.inputs[0])
        sbg = nt.nodes.new("ShaderNodeBackground")
        sbg.inputs["Color"].default_value = (1.0, 0.97, 0.9, 1)
        nt.links.new(amt.outputs[0], sbg.inputs["Strength"])
        add = nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(shader, add.inputs[0])
        nt.links.new(sbg.outputs["Background"], add.inputs[1])
        shader = add.outputs["Shader"]
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(shader, out.inputs["Surface"])
    scene().world = w
    return w


def setup_render(width, height, fps, samples, quality):
    sc = scene()
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
        e.identifier for e in sc.render.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.render.fps = fps
    sc.render.fps_base = 1.0
    sc.render.film_transparent = False
    sc.render.use_lock_interface = True
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 15
    ee = sc.eevee
    ee.taa_render_samples = samples
    ee.use_shadows = True
    try:
        ee.use_raytracing = quality == "high"
        ee.use_fast_gi = quality == "high"
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass
    _bloom(sc)


def _bloom(sc):
    """Soft glow around bright/emissive things via the compositor."""
    try:
        sc.use_nodes = True
        nt = sc.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        rl = nt.nodes.new("CompositorNodeRLayers")
        glare = nt.nodes.new("CompositorNodeGlare")
        glare.glare_type = "BLOOM"
        for name, val in (("Threshold", 1.0), ("Strength", 0.35), ("Size", 0.6)):
            if name in glare.inputs:
                glare.inputs[name].default_value = val
        comp = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
        nt.links.new(glare.outputs["Image"], comp.inputs["Image"])
    except Exception as exc:  # never fail a render because of a post effect
        print("[shot] bloom disabled:", exc)
        sc.use_nodes = False


def install_frame_handler(fps, offset=0.0):
    def _factory_frame(sc, depsgraph=None):
        apply((sc.frame_current - 1) / fps + offset)
    bpy.app.handlers.frame_change_pre.append(_factory_frame)
    return _factory_frame
