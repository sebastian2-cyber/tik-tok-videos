"""Low-poly 3D toolkit for the TikTok videos (runs inside Blender's Python / bpy)."""
import bpy, bmesh, math, os, random, hashlib
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")
TEX = os.path.join(ROOT, "cache", "tex")
os.makedirs(TEX, exist_ok=True)
FPS = 24
W, H = 540, 960


def rgb(h):
    """Hex colour -> linear RGBA (Blender works in linear space)."""
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, 1.0)


# ---------------------------------------------------------------- scene setup
def reset(quality="final"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = 8 if quality == "final" else 4
    cy.use_fast_gi = True
    cy.ao_bounces_render = 1
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.05
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.max_bounces = 2
    cy.diffuse_bounces = 1
    cy.glossy_bounces = 1
    cy.transmission_bounces = 2
    cy.transparent_max_bounces = 4
    cy.caustics_reflective = cy.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 92
    return sc


def world(color="#cfd8d3", strength=1.0):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = rgb(color)
    bg.inputs[1].default_value = strength
    return w


def sun(rot=(50, 10, 35), strength=3.0, color="#fff4e6", angle=12):
    d = bpy.data.lights.new("Sun", "SUN")
    d.energy, d.color, d.angle = strength, rgb(color)[:3], math.radians(angle)
    o = bpy.data.objects.new("Sun", d)
    bpy.context.collection.objects.link(o)
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


def area(loc, size=4, power=300, color="#ffffff", target=(0, 0, 1)):
    d = bpy.data.lights.new("Area", "AREA")
    d.energy, d.size, d.color = power, size, rgb(color)[:3]
    o = bpy.data.objects.new("Area", d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    return o


def point(loc, power=200, color="#ffe9c4", radius=0.2):
    d = bpy.data.lights.new("Pt", "POINT")
    d.energy, d.color, d.shadow_soft_size = power, rgb(color)[:3], radius
    o = bpy.data.objects.new("Pt", d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    return o


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- materials
_mats = {}


def mat(color, rough=0.85, emit=0.0, metal=0.0, alpha=1.0):
    key = (color, rough, emit, metal, alpha)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"M_{color}")
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Specular IOR Level"].default_value = 0.25
    if emit:
        p.inputs["Emission Color"].default_value = rgb(color)
        p.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
    _mats[key] = m
    return m


def img_mat(path, emit=0.0, rough=0.8, alpha=False):
    key = (path, emit, rough, alpha)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new("IMG_" + os.path.basename(path))
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    t.extension = "CLIP"
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Specular IOR Level"].default_value = 0.2
    if emit:
        nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit
    if alpha:
        nt.links.new(t.outputs["Alpha"], p.inputs["Alpha"])
    _mats[key] = m
    return m


# ---------------------------------------------------------------- geometry
def _link(o, parent=None):
    bpy.context.collection.objects.link(o)
    if parent:
        o.parent = parent
    return o


def empty(name="E", loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    return _link(o, parent)


def box(name, size, loc=(0, 0, 0), m=None, parent=None, pivot=(0, 0, 0), rot=(0, 0, 0),
        bevel=0.0, front=None, back=None, top=None):
    """Box of `size`; `pivot` (-1..1 per axis) is where the object origin sits on the box.
    front/back/top: optional materials for the -Y / +Y / +Z faces (UV 0..1)."""
    sx, sy, sz = size
    px, py, pz = pivot
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = {}
    for ix in (0, 1):
        for iy in (0, 1):
            for iz in (0, 1):
                vs[(ix, iy, iz)] = bm.verts.new(((ix - .5 - px / 2) * sx, (iy - .5 - py / 2) * sy, (iz - .5 - pz / 2) * sz))
    F = {
        "front": [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
        "back": [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)],
        "left": [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)],
        "right": [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
        "top": [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
        "bottom": [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)],
    }
    uvl = bm.loops.layers.uv.new("UV")
    mats = [m or mat("#cccccc")]
    extra = {"front": front, "back": back, "top": top}
    for fname, idx in F.items():
        f = bm.faces.new([vs[i] for i in idx])
        for loop, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop[uvl].uv = uv
        if extra.get(fname):
            if extra[fname] not in mats:
                mats.append(extra[fname])
            f.material_index = mats.index(extra[fname])
    bm.to_mesh(me)
    bm.free()
    for mm in mats:
        me.materials.append(mm)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    _link(o, parent)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL")
        b.width, b.segments = bevel, 2
        b.limit_method = "NONE"
    return o


def cyl(name, r, h, loc=(0, 0, 0), m=None, parent=None, verts=12, rot=(0, 0, 0), r2=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=h,
                                    location=loc, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m or mat("#cccccc"))
    if parent:
        o.parent = parent
    return o


def sphere(name, r, loc=(0, 0, 0), m=None, parent=None, sub=1, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(m or mat("#cccccc"))
    if parent:
        o.parent = parent
    return o


def plane_img(name, path, width, loc, rot=(90, 0, 0), emit=0.0, parent=None, alpha=False):
    im = Image.open(path)
    h = width * im.height / im.width
    return box(name, (width, 0.02, h), loc, m=mat("#20283a"), parent=parent, rot=rot,
               front=img_mat(path, emit=emit, alpha=alpha))


# ---------------------------------------------------------------- animation
def kf(o, f, loc=None, rot=None, scale=None, ease="BEZIER"):
    if loc is not None:
        o.location = loc
        o.keyframe_insert("location", frame=f)
    if rot is not None:
        o.rotation_euler = [math.radians(a) for a in rot]
        o.keyframe_insert("rotation_euler", frame=f)
    if scale is not None:
        o.scale = scale if hasattr(scale, "__len__") else (scale,) * 3
        o.keyframe_insert("scale", frame=f)
    if o.animation_data and o.animation_data.action and ease != "BEZIER":
        set_interp(o, ease)


def _fcurves(o):
    ad = o.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return list(act.fcurves)
    out = []  # Blender 4.4+/5.x layered actions
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def set_interp(o, mode="LINEAR"):
    for fc in _fcurves(o):
        for k in fc.keyframe_points:
            k.interpolation = mode


def shake(o, strength=0.01, scale=25, seed=0):
    """Subtle handheld noise on location (camera)."""
    o.keyframe_insert("location", frame=1)
    for fc in _fcurves(o):
        if fc.data_path == "location":
            n = fc.modifiers.new("NOISE")
            n.strength, n.scale, n.phase = strength, scale, seed * 7 + fc.array_index * 13


# ---------------------------------------------------------------- camera
def camera(loc, target, lens=35, loc2=None, target2=None, f0=1, f1=60, shake_amt=0.012):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.clip_start = 0.05
    c = _link(bpy.data.objects.new("Cam", cd))
    t = empty("CamTarget", target)
    con = c.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = t, "TRACK_NEGATIVE_Z", "UP_Y"
    bpy.context.scene.camera = c
    c.location = loc
    if loc2:
        kf(c, f0, loc=loc)
        kf(c, f1, loc=loc2)
    if target2:
        kf(t, f0, loc=target)
        kf(t, f1, loc=target2)
    if shake_amt:
        shake(t, shake_amt, 30, seed=3)
    return c, t


# ---------------------------------------------------------------- textures (PIL)
def font(name="Cabin-600", size=100):
    return ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)


def _cached(key, fn):
    path = os.path.join(TEX, hashlib.md5(repr(key).encode()).hexdigest()[:12] + ".png")
    if not os.path.exists(path):
        fn().save(path)
    return path


def sign_tex(text, bg="#1f3048", fg="#f4f1ea", w=1024, pad=60, fsize=170, fname="Cabin-500"):
    def make():
        f = font(fname, fsize)
        lines = text.split("\n")
        probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        ww = max(w, int(max(probe.textlength(ln, font=f) for ln in lines) + pad * 2.4))
        lh = int(fsize * 1.08)
        h = lh * len(lines) + pad * 2 - int(fsize * .1)
        im = Image.new("RGB", (ww, h), bg)
        d = ImageDraw.Draw(im)
        for i, ln in enumerate(lines):
            tw = d.textlength(ln, font=f)
            d.text(((ww - tw) / 2, pad + i * lh - fsize * 0.12), ln, font=f, fill=fg)
        return im
    return _cached(("sign", text, bg, fg, w, pad, fsize, fname), make)


def lcd_tex(text, w=512, h=256, bg="#a9c7a0", fg="#1d2a1f", fsize=150, fname="Montserrat-700"):
    def make():
        im = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(im)
        lines = text.split("\n")
        fs = fsize
        f = font(fname, fs)
        while max(d.textlength(l, font=f) for l in lines) > w * 0.9 or fs * 1.1 * len(lines) > h * 0.9:
            fs -= 4
            f = font(fname, fs)
        lh = fs * 1.1
        y = (h - lh * len(lines)) / 2
        for ln in lines:
            bb = d.textbbox((0, 0), ln, font=f)
            d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], y + (lh - (bb[3] - bb[1])) / 2 - bb[1]), ln, font=f, fill=fg)
            y += lh
        return im
    return _cached(("lcd", text, w, h, bg, fg, fsize, fname, 2), make)


def call_screen_tex(number="110", label="Notruf"):
    def make():
        w, h = 300, 560
        im = Image.new("RGB", (w, h), "#1b2430")
        d = ImageDraw.Draw(im)
        d.text((w / 2, 70), label, font=font("Montserrat-700", 34), fill="#9fb0c0", anchor="mm")
        d.text((w / 2, 190), number, font=font("Montserrat-800", 110), fill="#ffffff", anchor="mm")
        d.text((w / 2, 280), "wird angerufen …", font=font("Montserrat-700", 26), fill="#9fb0c0", anchor="mm")
        d.ellipse([w / 2 - 50, 420, w / 2 + 50, 520], fill="#e0453a")
        d.rounded_rectangle([w / 2 - 28, 462, w / 2 + 28, 478], 8, fill="#ffffff")
        return im
    return _cached(("call", number, label), make)


def tile_tex(color="#a9d3c0", line="#87b3a0", n=8, w=512, h=512, ratio=1.0, grout=4):
    def make():
        im = Image.new("RGB", (w, h), color)
        d = ImageDraw.Draw(im)
        cols, rows = n, max(1, int(n * ratio))
        for i in range(cols + 1):
            d.rectangle([i * w / cols - grout / 2, 0, i * w / cols + grout / 2, h], fill=line)
        for j in range(rows + 1):
            d.rectangle([0, j * h / rows - grout / 2, w, j * h / rows + grout / 2], fill=line)
        return im
    return _cached(("tile", color, line, n, w, h, ratio, grout), make)


def face_tex(expr="neutral", skin="#e9cdb4", stubble=True, mustache=False, seed=1, glasses=False, old=False, hairline=None):
    """Hand-drawn style face like the original: thin ink lines, heavy lids, dotted stubble."""
    def make():
        W_, H_ = 400, 640
        im = Image.new("RGB", (W_, H_), skin)
        d = ImageDraw.Draw(im)
        rnd = random.Random(seed)
        ink = (40, 32, 30)
        lw = 5
        ey = 255
        for side in (-1, 1):
            cx = W_ / 2 + side * 82
            ew, eh = 46, 26
            if expr == "shock":
                eh = 40
            d.ellipse([cx - ew, ey - eh, cx + ew, ey + eh], fill=(250, 248, 242), outline=ink, width=lw)
            pr = 9 if expr != "shock" else 7
            px = cx + (20 if expr == "side" else 4)
            d.ellipse([px - pr, ey - pr + 4, px + pr, ey + pr + 4], fill=ink)
            # heavy upper lid: cover the top part of the eye with skin, then draw the lid line
            lid = {"neutral": 0.42, "tired": 0.6, "angry": 0.55, "shock": 0.0, "smug": 0.58, "sad": 0.5,
                   "side": 0.42, "happy": 0.4, "talk": 0.42}.get(expr, .42)
            if lid:
                ly = ey - eh + 2 * eh * lid
                d.rectangle([cx - ew - 3, ey - eh - 4, cx + ew + 3, ly], fill=skin)
                d.line([cx - ew - 4, ly + (3 if side < 0 else -3) * (expr == "angry") * 3, cx + ew + 4,
                        ly - (3 if side < 0 else -3) * (expr == "angry") * 3], fill=ink, width=lw + 1)
            # brow
            by = ey - 62
            tilt = {"angry": 18, "sad": -16, "shock": -6, "smug": 8}.get(expr, 4)
            inner, outer = (cx - side * 40, by + tilt), (cx + side * 48, by - tilt * 0.4)
            if expr == "shock":
                inner, outer = (cx - side * 40, by - 18), (cx + side * 48, by - 22)
            d.line([inner, outer], fill=ink, width=12)
            if glasses:
                d.ellipse([cx - 60, ey - 50, cx + 60, ey + 50], outline=ink, width=6)
        if glasses:
            d.line([W_ / 2 - 22, ey, W_ / 2 + 22, ey], fill=ink, width=6)
        if hairline:
            pts = [(0, 0), (W_, 0), (W_, 70)]
            for i in range(9, -1, -1):
                pts.append((i * W_ / 9, 70 + (28 if i % 2 else 0) + rnd.randint(-6, 6)))
            d.polygon(pts, fill=hairline)
        # nose
        d.line([(W_ / 2 + 6, 290), (W_ / 2 - 10, 360), (W_ / 2 + 14, 368)], fill=ink, width=lw, joint="curve")
        # stubble
        if stubble:
            for _ in range(260):
                x = rnd.uniform(70, W_ - 70)
                y = rnd.uniform(395, 560)
                if abs(x - W_ / 2) < 75 and 420 < y < 470:
                    continue
                d.ellipse([x - 2.4, y - 2.4, x + 2.4, y + 2.4], fill=(70, 55, 50))
        if mustache:
            d.polygon([(W_ / 2 - 70, 425), (W_ / 2 + 70, 425), (W_ / 2 + 50, 400), (W_ / 2 - 50, 400)], fill=(60, 45, 40))
        my = 445
        if expr in ("shock",):
            d.ellipse([W_ / 2 - 26, my - 22, W_ / 2 + 26, my + 30], fill=(80, 30, 30), outline=ink, width=lw)
        elif expr == "talk":
            d.chord([W_ / 2 - 40, my - 18, W_ / 2 + 40, my + 28], 0, 180, fill=(80, 30, 30), outline=ink, width=lw)
        elif expr == "angry":
            d.arc([W_ / 2 - 45, my, W_ / 2 + 45, my + 40], 200, 340, fill=ink, width=lw + 1)
        elif expr == "smug":
            d.arc([W_ / 2 - 50, my - 40, W_ / 2 + 40, my + 10], 20, 150, fill=ink, width=lw + 1)
        elif expr == "happy":
            d.arc([W_ / 2 - 55, my - 45, W_ / 2 + 55, my + 15], 15, 165, fill=ink, width=lw + 1)
        elif expr == "sad":
            d.arc([W_ / 2 - 45, my + 5, W_ / 2 + 45, my + 50], 200, 340, fill=ink, width=lw)
        else:
            d.line([W_ / 2 - 32, my, W_ / 2 + 28, my + 3], fill=ink, width=lw + 1)
        if old:
            for k in range(3):
                d.arc([W_ / 2 - 90, 120 + k * 22, W_ / 2 + 90, 200 + k * 22], 200, 340, fill=ink, width=3)
        return im.filter(ImageFilter.SMOOTH)
    return _cached(("face", expr, skin, stubble, mustache, seed, glasses, old, hairline, 4), make)


# ---------------------------------------------------------------- characters
OUTFITS = {
    "suit": dict(body="#1d2433", shirt="#f2f0ea", tie="#b8262b", legs="#1d2433", shoes="#151515"),
    "police": dict(body="#53687c", shirt="#53687c", tie="#2c3a47", legs="#3a4a5a", shoes="#151515", cap="#2c3a47"),
    "pyjama": dict(body="#8ea6c6", shirt="#8ea6c6", tie=None, legs="#8ea6c6", shoes="#e9cdb4", stripes=True),
    "judge": dict(body="#141414", shirt="#f2f0ea", tie=None, legs="#141414", shoes="#151515", wig=True),
    "casual": dict(body="#c6643f", shirt="#c6643f", tie=None, legs="#3b4a6b", shoes="#2a2a2a"),
}


class Char:
    """Boxy character: tall rectangular head with drawn face, block body and limbs."""

    def __init__(self, name, outfit="suit", loc=(0, 0, 0), rot=0, expr="neutral", skin="#e9cdb4",
                 hair="#1b1b1b", mustache=False, stubble=True, seed=1, scale=1.0, glasses=False, bald=False):
        o = OUTFITS[outfit]
        self.name = name
        self.root = empty(name, loc)
        self.root.rotation_euler[2] = math.radians(rot)
        self.root.scale = (scale,) * 3
        self.hips = empty(name + "_hips", (0, 0, 0.92), self.root)
        body_m = mat(o["body"], .8)
        if o.get("stripes"):
            body_m = img_mat(stripe_tex(o["body"]))
        self.torso = box(name + "_torso", (0.56, 0.32, 0.74), (0, 0, 0), body_m, self.hips, pivot=(0, 0, -1),
                         front=self._front_tex(o, outfit))
        # head (tall box) sits on a short neck
        self.neck = empty(name + "_neck", (0, 0, 0.74), self.torso)
        box(name + "_neckb", (0.14, 0.14, 0.1), (0, 0, 0), mat(skin), self.neck, pivot=(0, 0, -1))
        self.face_args = (skin, stubble, mustache, seed, glasses, outfit == "judge", None if (bald or o.get("cap") or o.get("wig")) else hair)
        face = img_mat(face_tex(expr, *self.face_args))
        self.head = box(name + "_head", (0.4, 0.32, 0.64), (0, 0, 0.06), mat(skin), self.neck, pivot=(0, 0, -1),
                        front=face)
        box(name + "_ear", (0.42, 0.1, 0.12), (0, 0.02, 0.3), mat(skin), self.head)
        if o.get("cap"):
            box(name + "_cap", (0.44, 0.36, 0.13), (0, 0.01, 0.68), mat(o["cap"]), self.head)
            box(name + "_brim", (0.42, 0.11, 0.03), (0, -0.2, 0.645), mat("#1a222b", .4), self.head)
            box(name + "_capb", (0.08, 0.02, 0.06), (0, -0.182, 0.7), mat("#d9c27a", .3, metal=.6), self.head)
        elif o.get("wig"):
            for i, x in enumerate((-0.2, 0.2)):
                for k in range(3):
                    cyl(f"{name}_curl{i}{k}", 0.06, 0.13, (x * 1.15, 0.02, 0.5 - k * 0.12), mat("#eeeae0"), self.head,
                        rot=(90, 0, 0), verts=10)
            box(name + "_wigtop", (0.46, 0.36, 0.14), (0, 0.01, 0.66), mat("#eeeae0"), self.head)
        elif not bald:
            box(name + "_hair", (0.42, 0.34, 0.1), (0, 0.01, 0.66), mat(hair, .95), self.head)
            box(name + "_hairb", (0.42, 0.1, 0.34), (0, 0.13, 0.52), mat(hair, .95), self.head)
        # arms: pivot at shoulder
        self.arm_l = empty(name + "_arml", (-0.36, 0, 0.7), self.torso)
        self.arm_r = empty(name + "_armr", (0.36, 0, 0.7), self.torso)
        for a in (self.arm_l, self.arm_r):
            box(a.name + "b", (0.15, 0.17, 0.66), (0, 0, 0), body_m, a, pivot=(0, 0, 1))
            box(a.name + "h", (0.12, 0.13, 0.14), (0, 0, -0.73), mat(skin), a)
        self.leg_l = empty(name + "_legl", (-0.14, 0, 0), self.hips)
        self.leg_r = empty(name + "_legr", (0.14, 0, 0), self.hips)
        for g in (self.leg_l, self.leg_r):
            box(g.name + "b", (0.22, 0.24, 0.86), (0, 0, 0), mat(o["legs"], .85), g, pivot=(0, 0, 1))
            box(g.name + "s", (0.22, 0.34, 0.08), (0, -0.05, -0.88), mat(o["shoes"], .5), g)
        self.props = []

    def _front_tex(self, o, outfit):
        if outfit in ("suit", "police", "judge"):
            return img_mat(outfit_tex(outfit, o))
        return None

    # ---- poses / animation
    def pose(self, f, arm_l=None, arm_r=None, head=None, torso=None, legs=None, loc=None, rot=None):
        """Angles in degrees (x,y,z). arm X-rotation negative lifts arm forward."""
        if arm_l is not None:
            kf(self.arm_l, f, rot=arm_l)
        if arm_r is not None:
            kf(self.arm_r, f, rot=arm_r)
        if head is not None:
            kf(self.neck, f, rot=head)
        if torso is not None:
            kf(self.torso, f, rot=torso)
        if legs is not None:
            kf(self.leg_l, f, rot=legs[0])
            kf(self.leg_r, f, rot=legs[1])
        if loc is not None:
            kf(self.root, f, loc=loc)
        if rot is not None:
            kf(self.root, f, rot=(0, 0, rot))

    def idle(self, f0, f1, amount=1.0, seed=0):
        """Subtle life: weight shift, head tilt, small arm sway."""
        r = random.Random(seed)
        step = 24
        f = f0
        while f <= f1 + step:
            a = amount
            kf(self.neck, f, rot=(r.uniform(-3, 3) * a, r.uniform(-4, 4) * a, r.uniform(-6, 6) * a))
            kf(self.torso, f, rot=(r.uniform(-1.5, 1.5) * a, r.uniform(-2, 2) * a, 0))
            f += step + r.randint(-6, 6)

    def arms_down(self, f, spread=6):
        self.pose(f, arm_l=(0, -spread, 0), arm_r=(0, spread, 0))

    def walk(self, f0, f1, start, end, period=16, swing=28):
        kf(self.root, f0, loc=start)
        kf(self.root, f1, loc=end)
        set_interp(self.root, "LINEAR")
        f = f0
        s = 1
        while f <= f1:
            kf(self.leg_l, f, rot=(swing * s, 0, 0))
            kf(self.leg_r, f, rot=(-swing * s, 0, 0))
            kf(self.arm_l, f, rot=(-swing * 0.8 * s, -5, 0))
            kf(self.arm_r, f, rot=(swing * 0.8 * s, 5, 0))
            kf(self.hips, f, loc=(0, 0, 0.92))
            kf(self.hips, f + period / 4, loc=(0, 0, 0.96))
            f += period / 2
            s = -s
        for g in (self.leg_l, self.leg_r, self.arm_l, self.arm_r):
            kf(g, f1 + 6, rot=(0, 0, 0))

    def hold(self, obj, hand="r", offset=(0, -0.02, -0.82)):
        arm = self.arm_r if hand == "r" else self.arm_l
        obj.parent = arm
        obj.location = offset
        return obj

    def set_face(self, expr):
        """Swap the face drawing (whole shot)."""
        self.head.data.materials[1] = img_mat(face_tex(expr, *self.face_args))


def stripe_tex(color, w=256, h=256):
    def make():
        im = Image.new("RGB", (w, h), color)
        d = ImageDraw.Draw(im)
        for i in range(0, w, 32):
            d.rectangle([i, 0, i + 10, h], fill="#eef0f5")
        return im
    return _cached(("stripe", color, w, h), make)


def outfit_tex(kind, o):
    def make():
        W_, H_ = 400, 520
        im = Image.new("RGB", (W_, H_), o["body"])
        d = ImageDraw.Draw(im)
        if kind == "suit":
            d.polygon([(130, 0), (270, 0), (200, 230)], fill=o["shirt"])
            d.polygon([(186, 20), (214, 20), (226, 330), (200, 370), (174, 330)], fill=o["tie"])
            d.polygon([(130, 0), (200, 230), (160, 300), (100, 0)], fill="#151b27")
            d.polygon([(270, 0), (200, 230), (240, 300), (300, 0)], fill="#151b27")
            d.ellipse([290, 330, 300, 340], fill="#0d1018")
        elif kind == "police":
            d.polygon([(150, 0), (250, 0), (200, 70)], fill="#3c4d5e")
            d.line([(200, 70), (200, H_)], fill="#3c4d5e", width=6)
            for y in (130, 220, 310, 400):
                d.ellipse([194, y, 206, y + 12], fill="#2a3540")
            d.polygon([(255, 120), (300, 120), (300, 165), (277, 182), (255, 165)], fill="#d9c27a")
            d.rectangle([80, 120, 150, 180], outline="#3c4d5e", width=5)
            d.rectangle([250, 210, 320, 270], outline="#3c4d5e", width=5)
            d.rectangle([0, 470, W_, 520], fill="#1d1d1d")
            d.rectangle([180, 472, 220, 518], fill="#c0b070")
        elif kind == "judge":
            d.polygon([(150, 0), (250, 0), (200, 120)], fill=o["shirt"])
            d.rectangle([190, 40, 210, 90], fill="#ffffff")
        return im
    return _cached(("outfit", kind, tuple(sorted((k, str(v)) for k, v in o.items())), 2), make)


# ---------------------------------------------------------------- sets & props
def floor(color="#d8d2c4", size=40, loc=(0, 0, 0), m=None):
    return box("Floor", (size, size, 0.1), loc, m or mat(color, .9), pivot=(0, 0, 1))


def room(w=6, d=6, h=3.2, wall="#e8c9b8", floor_m=None, lower=None, lower_h=1.2, open_side="front", ceiling=True):
    """Simple room. Back wall at +Y, side walls at ±X; front (-Y) open for the camera."""
    g = empty("Room")
    box("RFloor", (w, d, 0.1), (0, 0, 0), floor_m or mat("#d9d4c8", .9), g, pivot=(0, 0, 1))
    walls = [("back", (w, 0.1, h), (0, d / 2, h / 2)), ("left", (0.1, d, h), (-w / 2, 0, h / 2)),
             ("right", (0.1, d, h), (w / 2, 0, h / 2))]
    for n, s, l in walls:
        box("Wall_" + n, s, l, mat(wall, .95), g)
        if lower:
            ls = (s[0] + (0.02 if n == "back" else 0.02), s[1] + 0.02, lower_h)
            ll = (l[0] - (0.01 if n == "left" else -0.01 if n == "right" else 0), l[1] - (0.01 if n == "back" else 0), lower_h / 2)
            o = box("Lower_" + n, ls, ll, lower, g)
            # tiled texture repeated via UV scaling
            for poly in o.data.uv_layers[0].data:
                poly.uv = (poly.uv[0] * max(s[0], s[1]) * 2.2, poly.uv[1] * lower_h * 2.2)
    if ceiling:
        box("Ceil", (w, d, 0.1), (0, 0, h), mat("#efe9e0", .95), g, pivot=(0, 0, -1))
    return g


def uv_scale(o, sx, sy):
    for l in o.data.uv_layers[0].data:
        l.uv = (l.uv[0] * sx, l.uv[1] * sy)


def tiled_mat(tex):
    m = img_mat(tex, rough=0.4)
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.extension = "REPEAT"
    return m


def bars(loc=(0, 0, 0), width=3.0, height=3.0, n=10, color="#9fb0b8", parent=None):
    g = empty("Bars", loc, parent)
    m = mat(color, .45, metal=.3)
    for i in range(n + 1):
        x = -width / 2 + i * width / n
        cyl(f"bar{i}", 0.035, height, (x, 0, height / 2), m, g, verts=8)
    box("bar_top", (width + .1, .12, .12), (0, 0, height), m, g)
    box("bar_mid", (width + .1, .08, .08), (0, 0, height * 0.42), m, g)
    box("bar_bot", (width + .1, .12, .1), (0, 0, 0.05), m, g)
    return g


def prison_cell(sign_text="10 JAHRE", number="18", loc=(0, 0, 0)):
    """Cell like in the originals: pale walls, bars at the front, navy sign above."""
    g = empty("Cell", loc)
    room(4, 4, 3.4, wall="#e9e4d8", floor_m=mat("#d6d2c8", .9), ceiling=False).parent = g
    box("bed", (1.9, 0.8, 0.12), (-0.8, 1.45, 0.55), mat("#c9ccc6"), g)
    box("bedpad", (1.85, 0.75, 0.12), (-0.8, 1.45, 0.66), mat("#2f6f6a"), g)
    box("bedleg", (1.9, 0.8, 0.5), (-0.8, 1.45, 0.25), mat("#9fb0b8", .5), g)
    bars((0, -1.95, 0), 4.0, 3.0, 12, parent=g)
    box("signwall", (4.2, 0.12, 0.8), (0, -2.0, 3.35), mat("#e9e4d8"), g)
    sign = plane_img("sign", sign_tex(sign_text), 2.2, (0, -2.1, 3.35), rot=(0, 0, 0), parent=g)
    plane_img("num", sign_tex(number, bg="#f4f1ea", fg="#1f3048", w=300, fsize=150), 0.35, (0, -2.1, 3.92),
              rot=(0, 0, 0), parent=g)
    return g, sign


def police_car(name="Police", loc=(0, 0, 0), rot=0, lights_on=True):
    g = empty(name, loc)
    g.rotation_euler[2] = math.radians(rot)
    white, dark, glass = mat("#f1f1ee", .35), mat("#1c2430", .5), mat("#8fb4c6", .1)
    box(name + "_body", (1.9, 4.2, 0.75), (0, 0, 0.62), white, g, bevel=0.05)
    box(name + "_cab", (1.7, 2.1, 0.62), (0, 0.2, 1.3), white, g, bevel=0.05)
    box(name + "_win", (1.72, 1.9, 0.42), (0, 0.2, 1.32), glass, g)
    box(name + "_stripe", (1.92, 3.6, 0.16), (0, 0, 0.72), mat("#1f3a6b"), g)
    for x in (-0.85, 0.85):
        for y in (-1.35, 1.35):
            cyl(name + "_wh", 0.36, 0.3, (x, y, 0.36), dark, g, rot=(0, 90, 0), verts=14)
    box(name + "_barL", (0.6, 0.3, 0.16), (-0.33, 0.2, 1.7), mat("#e33b3b", .3, emit=6 if lights_on else 0), g)
    box(name + "_barR", (0.6, 0.3, 0.16), (0.33, 0.2, 1.7), mat("#3b6be3", .3, emit=6 if lights_on else 0), g)
    return g


def phone(name="Phone", screen=None, size=1.0):
    p = box(name, (0.09 * size, 0.03 * size, 0.17 * size), (0, 0, 0), mat("#1b1b1b", .3))
    if screen:
        tex = call_screen_tex(screen)
        box(name + "_scr", (0.08 * size, 0.005, 0.15 * size), (0, 0.016 * size, 0), mat("#222"), p,
            back=img_mat(tex, emit=1.2))
    else:
        box(name + "_scr", (0.08 * size, 0.005, 0.15 * size), (0, -0.016 * size, 0), mat("#9cc9e8", .2, emit=1.5), p)
    return p


def table(loc=(0, 0, 0), size=(1.6, 0.9, 0.78), top="#7a5a43", parent=None):
    g = empty("Table", loc, parent)
    box("ttop", (size[0], size[1], 0.07), (0, 0, size[2]), mat(top, .6), g)
    for x in (-1, 1):
        for y in (-1, 1):
            box("tleg", (0.07, 0.07, size[2]), (x * (size[0] / 2 - .06), y * (size[1] / 2 - .06), size[2] / 2), mat("#3a3a3a", .5), g)
    return g


def hanging_lamp(loc, power=150, color="#ffe2b0"):
    g = empty("Lamp", loc)
    cyl("cord", 0.01, 1.2, (0, 0, 0.6), mat("#222"), g, verts=6)
    cyl("shade", 0.32, 0.22, (0, 0, 0), mat("#2d3b36", .5), g, verts=16, r2=0.06)
    sphere("bulb", 0.08, (0, 0, -0.06), mat("#fff3d0", emit=8), g)
    l = point((0, 0, -0.2), power, color, 0.1)
    l.parent = g
    return g


def sweat(parent, loc, f0, f1, period=18, n=3, seed=0):
    """Drops that pop out and fall."""
    r = random.Random(seed)
    m = mat("#8fd0ef", .1, emit=0.4)
    for i in range(n):
        d = sphere(f"drop{i}", 0.04, (0, 0, 0), m, parent, sub=2, scale=(0.7, 0.7, 1.2))
        x, y, z = loc
        x += r.uniform(-0.04, 0.04)
        f = f0 + i * period // n
        while f < f1:
            kf(d, f - 1, loc=(x, y, z), scale=0.001)
            kf(d, f, loc=(x, y, z), scale=1)
            kf(d, f + period, loc=(x + r.uniform(-.1, .1), y, z - 0.35), scale=0.6)
            kf(d, f + period + 1, scale=0.001)
            f += period
    return


def render(out_dir, f0, f1):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = f0, f1
    os.makedirs(out_dir, exist_ok=True)
    sc.render.filepath = os.path.join(out_dir, "f_")
    bpy.ops.render.render(animation=True)


# ---------------------------------------------------------------- reusable sets (v2)
def bathroom():
    """Peach walls, mint tiles, mirror and sink on the back wall (like the original's bathroom)."""
    world("#e9d6c8", 0.7)
    g = room(5, 5, 3.0, wall="#ecc7b1", floor_m=tiled_mat(tile_tex("#e9e6df", "#cfcac0", 4, 256, 256)),
             lower=tiled_mat(tile_tex("#a9d3c0", "#8fbfa9", 4, 256, 256)), lower_h=1.3)
    uv_scale(bpy.data.objects["RFloor"], 6, 6)
    box("mirror_frame", (1.3, 0.06, 0.95), (0.9, 2.44, 1.85), mat("#d9d9d4", .4), g)
    box("mirror", (1.2, 0.07, 0.85), (0.9, 2.43, 1.85), mat("#b9d1d8", 0.05, metal=0.7), g)
    box("sink", (0.9, 0.5, 0.18), (0.9, 2.2, 0.95), mat("#f4f4f2", .3), g)
    box("sinkleg", (0.25, 0.25, 0.9), (0.9, 2.3, 0.45), mat("#f4f4f2", .3), g)
    box("towel", (0.5, 0.06, 0.7), (-1.6, 2.44, 1.4), mat("#e07a5f", .95), g)
    box("towelbar", (0.6, 0.06, 0.05), (-1.6, 2.42, 1.75), mat("#c9c9c9", .3, metal=.6), g)
    sun((58, 0, 25), 2.2, "#fff1e2")
    area((1.6, -2.2, 2.7), 3, 320, target=(0, 0.5, 1.2))
    point((0, 0.5, 2.8), 120, "#fff1dc", 0.6)
    return g


def interrogation():
    world("#2a3236", 0.25)
    g = room(5, 5, 3.0, wall="#55636a", floor_m=mat("#3a3f42", .9), ceiling=True)
    box("mirror1", (2.0, 0.06, 1.0), (0, 2.43, 1.6), mat("#20292d", 0.08, metal=0.6), g)
    t = table((0, 0.3, 0), (1.5, 0.9, 0.78), top="#6b6f70")
    hanging_lamp((0, 0.3, 2.1), 260)
    area((0, -3, 2), 2, 50, "#9fb6c8", target=(0, 0.3, 1))
    return g, t


def scale_prop(name="Waage", loc=(0, 0, 0), display="140 kg", color="#f2f2f0", parent=None, rot=0, disp_w=0.26):
    g = empty(name, loc, parent)
    g.rotation_euler[2] = math.radians(rot)
    box(name + "_body", (0.46, 0.46, 0.06), (0, 0, 0.03), mat(color, .35), g, bevel=0.015)
    box(name + "_pad", (0.4, 0.28, 0.005), (0, 0.06, 0.062), mat("#d7d7d3", .8), g)
    dh = 0.085 if "\n" not in display else 0.13
    disp = box(name + "_disp", (disp_w, dh, 0.01), (0, -0.175 - (dh - 0.085) / 2, 0.062), mat("#333"), g,
               top=img_mat(lcd_tex(display, int(512 * disp_w / 0.26), int(256 * dh / 0.085)), emit=0.6))
    return g, disp


def hang_sign(text, loc, f_in=4, width=2.0, rot=(0, 0, 0), parent=None, drop=1.2):
    """Navy sign that drops in from above with a little bounce (like 'IDENTITY THEFT')."""
    s = plane_img("Sign_" + text[:8], sign_tex(text), width, loc, rot=rot, parent=parent)
    x, y, z = loc
    kf(s, 1, loc=(x, y, z + drop))
    kf(s, f_in, loc=(x, y, z + drop))
    kf(s, f_in + 5, loc=(x, y, z - 0.06))
    kf(s, f_in + 9, loc=(x, y, z + 0.02))
    kf(s, f_in + 12, loc=(x, y, z))
    return s
