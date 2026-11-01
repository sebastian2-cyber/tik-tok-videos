"""Die Waage — erstes deutsches Video im Stil 'absurde Straftat -> Polizei -> Gefängnis'."""
from studio import *

VOICE = dict(voice="de-DE-ConradNeural", rate="+6%", pitch="-2Hz")
BPM = 96
SEED = 3


def man(loc=(0, 0, 0), rot=0, expr="neutral"):
    return Char("man", "pyjama", loc, rot=rot, expr=expr, seed=2, hair="#2a1f1a")


def cop(name, loc, rot=0, expr="neutral", seed=5, mustache=True):
    return Char(name, "police", loc, rot=rot, expr=expr, mustache=mustache, seed=seed)


# ---------------------------------------------------------------- shots
def s_step_on(n):
    bathroom()
    scale_prop("Waage", (0, -0.2, 0), "140 kg")
    m = man((0.0, 0.55, 0))
    # step forward onto the scale
    m.walk(1, 22, (0, 0.55, 0), (0, -0.15, 0.06), period=14, swing=22)
    m.idle(26, n, 0.8, seed=1)
    m.pose(26, arm_l=(0, -5, 0), arm_r=(0, 5, 0))
    camera((0.45, -2.3, 0.75), (0, 0, 1.25), lens=24, loc2=(0.3, -1.95, 0.8), f0=1, f1=n)


def s_display_140(n):
    bathroom()
    s, d = scale_prop("Waage", (0, 0, 0), "140 kg")
    m = man((0, 0.1, 0.06))
    m.idle(1, n, 0.4)
    camera((0, -0.36, 1.5), (0, -0.15, 0.06), lens=48, loc2=(0, -0.34, 1.38), target2=(0, -0.16, 0.06), f0=1, f1=n, shake_amt=0.004)


def s_verleumdung(n):
    bathroom()
    scale_prop("Waage", (0, 0, 0), "140 kg")
    m = man((0, 0.05, 0.06), expr="shock")
    m.pose(1, arm_l=(0, -6, 0), arm_r=(0, 6, 0), head=(-6, 0, 0))
    m.pose(n, arm_l=(-10, -30, 0), arm_r=(-10, 30, 0), head=(-10, 0, 0))
    hang_sign("VERLEUMDUNG", (0, -0.25, 2.62), f_in=3, width=1.0)
    camera((0.12, -1.95, 2.0), (0, 0.05, 2.12), lens=30, loc2=(0.08, -1.7, 2.0), f0=1, f1=n)


def s_call_police(n):
    """Insert shot: angry hand dials 110."""
    bathroom()
    p = phone(screen="110", size=1.6)
    p.location = (0.02, -0.6, 1.5)
    hand = box("hand", (0.17, 0.1, 0.2), (0.0, -0.07, -0.12), mat("#e9cdb4"), p)
    sleeve = box("sleeve", (0.2, 0.2, 0.9), (0.03, -0.09, -0.62), img_mat(stripe_tex("#8ea6c6")), p, rot=(0, -12, 0))
    thumb = box("thumb", (0.04, 0.04, 0.09), (0.11, 0.01, -0.06), mat("#e9cdb4"), p, rot=(0, -25, 0))
    kf(p, 1, rot=(-8, 0, 180 + 4))
    kf(p, n, rot=(-4, 0, 180 - 3))
    # thumb taps the screen
    for f in range(4, n, 9):
        kf(thumb, f, loc=(0.11, 0.01, -0.06))
        kf(thumb, f + 3, loc=(0.08, 0.03, -0.03))
    camera((0.05, -1.25, 1.62), (0.02, -0.6, 1.5), lens=42, loc2=(0.04, -1.12, 1.6), f0=1, f1=n)


def s_two_cops(n):
    bathroom()
    m = man((0.7, 0.4, 0.0), rot=-30)
    m.idle(1, n, 0.5)
    a = cop("cop1", (-2.0, -0.4, 0), rot=-90, seed=5)
    b = cop("cop2", (-2.9, -0.2, 0), rot=-90, seed=8, mustache=False)
    a.walk(1, 34, (-2.6, -0.3, 0), (-0.6, -0.3, 0), period=16)
    b.walk(1, 40, (-3.4, 0.2, 0), (-1.2, 0.3, 0), period=16)
    a.pose(40, rot=-20)
    b.pose(46, rot=-15)
    camera((0.4, -3.4, 1.4), (-0.4, 0, 1.4), lens=24, loc2=(0.2, -3.1, 1.45), f0=1, f1=n)


def s_interrogate(n):
    g, t = interrogation()
    scale_prop("Waage", (0, 0.3, 0.82), "140 kg")
    a = cop("cop1", (-0.85, 0.95, 0), rot=20, seed=5)
    b = cop("cop2", (0.85, 0.95, 0), rot=-20, expr="angry", seed=8, mustache=False)
    a.pose(1, arm_l=(-38, -6, 0), arm_r=(-38, 6, 0), torso=(16, 0, 0), head=(10, 0, -10))
    b.pose(1, arm_l=(0, -6, 0), arm_r=(0, 6, 0), head=(12, 0, 10))
    b.pose(int(n * 0.45), arm_r=(-75, 10, 0))
    b.pose(int(n * 0.6), arm_r=(-45, 10, 0))
    b.pose(int(n * 0.75), arm_r=(-75, 10, 0))
    a.idle(1, n, 0.5, 1)
    area((0, -2.5, 2.2), 2.5, 160, "#b7cde0", target=(0, 0.5, 1.2))
    camera((0.25, -1.9, 1.75), (0, 0.4, 1.25), lens=26, loc2=(0.2, -1.6, 1.7), f0=1, f1=n)


def s_display_dark(n):
    interrogation()
    scale_prop("Waage", (0, 0.3, 0.82), "140 kg")
    camera((0, -0.35, 1.25), (0, 0.18, 0.86), lens=40, loc2=(0, -0.2, 1.15), f0=1, f1=n)


def s_cop_on_scale(n):
    g, t = interrogation()
    bpy.data.objects["Table"].location = (0, 1.6, 0)
    bpy.data.objects["Lamp"].location = (1.0, 1.2, 2.75)
    scale_prop("Waage", (0, 0.3, 0), "...")
    a = cop("cop1", (0, 0.35, 0.06), seed=5)
    a.idle(1, n, 0.5)
    a.pose(1, head=(14, 0, 0))
    b = cop("cop2", (1.1, 0.0, 0), rot=60, seed=8, mustache=False)
    area((0.5, -2.5, 2.4), 2.5, 220, "#c7d8e8", target=(0, 0.3, 1.2))
    b.pose(1, arm_l=(0, -6, 0), arm_r=(0, 6, 0), head=(10, 0, -10))
    camera((0.6, -2.6, 1.9), (0.25, 0.2, 1.2), lens=26, loc2=(0.45, -2.3, 1.85), f0=1, f1=n)


def s_donuts(n):
    interrogation()
    bpy.data.objects["Table"].location = (0, 1.6, 0)
    bpy.data.objects["Lamp"].location = (1.0, 1.2, 2.75)
    scale_prop("Waage", (0, 0.3, 0), "WENIGER\nDONUTS", disp_w=0.3)
    area((0, -0.6, 2.3), 1.5, 90, "#dfe8f0", target=(0, 0.2, 0.1))
    a = cop("cop1", (0, 0.35, 0.06), seed=5)
    camera((0, -0.12, 1.45), (0, 0.13, 0.06), lens=44, loc2=(0, -0.1, 1.35), target2=(0, 0.13, 0.06), f0=1, f1=n, shake_amt=0.004)


def s_beleidigung(n):
    interrogation()
    bpy.data.objects["Table"].location = (0, 1.6, 0)
    bpy.data.objects["Lamp"].location = (1.0, 1.2, 2.75)
    a = cop("cop1", (0, 0.35, 0.06), expr="angry", seed=5)
    a.pose(1, head=(10, 0, 0))
    a.pose(10, head=(0, 0, 0))
    a.idle(12, n, 0.4)
    hang_sign("BEAMTEN-\nBELEIDIGUNG", (0, 0.05, 2.75), f_in=3, width=0.95)
    area((0, -2, 2.4), 2, 120, "#cfe0ee", target=(0, 0.3, 2.1))
    camera((0.12, -1.8, 2.45), (0, 0.3, 2.2), lens=30, loc2=(0.08, -1.55, 2.4), f0=1, f1=n)


def s_prison(n):
    world("#d9d8d0", 0.8)
    cell, sign = prison_cell("10 JAHRE", "18")
    floor("#cfcbc0")
    s, d = scale_prop("Waage", (-0.6, 1.4, 0.72), "140 kg", rot=-10)
    sun((50, 0, 20), 2.4)
    area((0, -4, 3), 4, 400, target=(0, 0, 1.5))
    point((0, 0.5, 3.0), 100, "#fff2dc", 0.5)
    camera((0.5, -6.2, 2.2), (0, -1.2, 2.05), lens=30, loc2=(0.3, -5.3, 2.1), target2=(-0.1, -1.0, 1.95), f0=1, f1=n)


def s_new_scale(n):
    bathroom()
    scale_prop("Waage2", (0, -0.2, 0), "70 kg", color="#f2b8c6")
    m = man((0.0, 0.55, 0), expr="happy")
    m.walk(1, 22, (0, 0.55, 0), (0, -0.15, 0.06), period=14, swing=22)
    m.idle(26, n, 0.8, seed=4)
    camera((-0.45, -2.3, 0.75), (0, 0, 1.25), lens=24, loc2=(-0.3, -1.95, 0.8), f0=1, f1=n)


def s_display_70(n):
    bathroom()
    scale_prop("Waage2", (0, 0, 0), "70 kg", color="#f2b8c6")
    m = man((0, 0.1, 0.06), expr="happy")
    m.idle(1, n, 0.4)
    camera((0, -0.36, 1.5), (0, -0.15, 0.06), lens=48, loc2=(0, -0.34, 1.38), target2=(0, -0.16, 0.06), f0=1, f1=n, shake_amt=0.004)


def s_not_broken(n):
    bathroom()
    s, d = scale_prop("Waage2", (0, 0, 0), "70 kg", color="#f2b8c6")
    m = man((0, 0.1, 0.06), expr="happy")
    m.idle(1, n, 0.5)
    camera((0.7, -1.3, 0.55), (0, 0, 0.35), lens=28, loc2=(0.55, -1.1, 0.5), f0=1, f1=n)


def s_angst(n):
    bathroom()
    s, d = scale_prop("Waage2", (0, 0, 0), "70 kg", color="#f2b8c6")
    m = man((0, 0.15, 0.06), expr="happy")
    m.idle(1, n, 0.3)
    # the scale trembles under him
    f = 1
    while f < n:
        kf(s, f, loc=(0.012 * ((f // 2) % 2 * 2 - 1), 0, 0))
        f += 2
    set_interp(s, "CONSTANT")
    sweat(s, (0.25, -0.2, 0.09), 4, n, period=16, n=3, seed=2)
    sweat(s, (-0.25, -0.2, 0.09), 10, n, period=18, n=3, seed=5)
    camera((0.0, -0.9, 0.42), (0, -0.05, 0.12), lens=32, loc2=(0, -0.75, 0.38), f0=1, f1=n)


SHOTS = [
    dict(text="Dieser Mann ist auf seine Waage gestiegen.", hl=["Waage"], scene=s_step_on, pad=0.2),
    dict(text="Sie zeigte 140 Kilo.", hl=["140", "Kilo."], scene=s_display_140, sfx=[("beep", 0.1, 0.8)]),
    dict(text="Das war Verleumdung.", hl=["Verleumdung."], scene=s_verleumdung, sfx=[("boom", 0.2, 0.8)]),
    dict(text="Also rief er die Polizei.", hl=["Polizei."], scene=s_call_police, sfx=[("phone", 0.3, 0.6)]),
    dict(text="Sie schickten ihre zwei besten Männer.", hl=["besten", "Männer."], scene=s_two_cops,
         sfx=[("siren", 0.0, 0.5), ("door", 0.4, 0.6)], pad=0.2),
    dict(text="Sie haben die Waage verhört.", hl=["verhört."], scene=s_interrogate, pad=0.3),
    dict(text="Sie blieb bei ihrer Aussage.", hl=["Aussage."], scene=s_display_dark),
    dict(text="Also stellte sich ein Beamter selbst drauf.", hl=["Beamter"], scene=s_cop_on_scale),
    dict(text="Die Waage zeigte: „Weniger Donuts.“", hl=["Weniger", "Donuts.“"], scene=s_donuts,
         sfx=[("beep", 0.9, 0.8)], pad=0.2),
    dict(text="Das war Beamtenbeleidigung.", hl=["Beamtenbeleidigung."], scene=s_beleidigung,
         sfx=[("boom", 0.2, 0.8)]),
    dict(text="Zehn Jahre Gefängnis.", hl=["Gefängnis."], scene=s_prison,
         sfx=[("jail", 0.15, 0.8), ("gavel", 0.0, 0.6)], pad=0.4),
    dict(text="Der Mann hat jetzt eine neue Waage.", hl=["neue", "Waage."], scene=s_new_scale, pad=0.2),
    dict(text="Sie zeigt immer 70 Kilo.", hl=["70", "Kilo."], scene=s_display_70, sfx=[("beep", 0.1, 0.8)]),
    dict(text="Sie ist nicht kaputt.", hl=["kaputt."], scene=s_not_broken),
    dict(text="Sie hat einfach Angst.", hl=["Angst."], scene=s_angst, pad=1.0),
]
