"""Procedurally builds the drivable crawler excavator for the BigMachines mod.

Run headless from the project root:
    blender --background --python blender/build_excavator.py

Outputs:
    BigMachines/excavator/bm_excavator.p3d          the machine (MLOD; tools/build.sh binarizes it)
    BigMachines/excavator/proxy/bm_exc_roller.p3d   the sprocket/idler shown at each physics wheel
    models/excavator.blend, models/excavator_preview.png

Tracks, rollers, LOD assembly and export: crawler.py. The upper house (cab, engine,
counterweight, the driver and the arm) is the model's root; everything below the slewing
ring is the "undercarriage" bone. DayZ fixes a seated player where the seat is in the
modelled pose, so the house can't turn on the model: slewing turns the whole machine and the
undercarriage turns back the other way, keeping the tracks where they were (BM_Excavator.c).
Arm: boom ("boom"), stick ("stick", child of boom), bucket ("bucket", child of stick). Each
hydraulic cylinder's barrel swings about its base in its own bone (boom_cyl, stick_cyl,
bucket_cyl; children of the part the base is on) and its rod rides the part it pushes.
model.cfg in BigMachines/ animates them; the angles it needs are printed here.

Coordinates: see rv.py (Blender X right, Y forward, Z up; origin on the ground, centred).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawler  # noqa: E402
import rv  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402
from rv import MeshBuilder, X_AXIS_ROT  # noqa: E402

MODEL_DIR = os.path.join(crawler.ROOT, "BigMachines", "excavator")
TRACKS = crawler.Tracks(x=1.20, width=0.60, wheelbase=3.0, radius=0.36, thickness=0.07,
                        roller_path="BigMachines\\excavator\\proxy\\bm_exc_roller.p3d")
BATTERY_POS = (0.0, 0.92, 0.62)     # on the front of the car body, between the tracks

UNDER = ("undercarriage",)           # the bone for everything below the slewing ring

# --- Upper house (the model's root) ---
DECK_Z = 1.07                       # underside of the house, on the slewing ring
FLOOR_Z = 1.27                      # deck top / cab floor
CAB = (-1.25, -0.45, -0.30, 1.20)   # x0, y0, x1, y1: front left
CREW_POS = (-0.775, 0.0, 1.69)      # driver's seat proxy, on the cushion
TAIL_R = 2.35                       # counterweight radius round the slewing axis

# --- Arm, in the (y, z) plane at x = 0; modelled at rest (every joint at angle 0) ---
BOOM_FOOT = (1.0, 1.7)              # boom pivot on the house
BOOM_KNEE = (3.2, 3.6)
BOOM_TIP = (5.6, 3.4)               # stick pivot
STICK_TOP = (5.3, 4.3)              # stick lever: the stick cylinder's mount
BUCKET_PIN = (6.2, 1.2)             # bucket pivot, bottom of the stick
BOOM_CYL = ((1.45, 1.35), (2.7, 2.8))    # base on the house, mount on the boom
STICK_CYL = ((2.7, 3.95), STICK_TOP)     # base on a bracket on the boom, mount on the stick
BUCKET_CYL = ((5.85, 3.35), (6.55, 1.5))  # base on the stick's outer face, mount on the bucket

# Joints: (angle at phase 0, angle at phase 1, speed). Angles in degrees from the modelled
# pose, + turning the part's far end up-and-out in the (y, z) plane (counter-clockwise seen
# from +X): phase 1 raises the boom, swings the stick out and curls the bucket. The bucket's
# teeth face the machine, so curling turns it the other way (-). Speed: phase per second
# (config animPeriod is 1 / speed).
JOINTS = {
    "boom": (-35, 30, 0.20),
    "stick": (-45, 40, 0.20),
    "bucket": (35, -95, 0.25),
}

MASSES = {
    "m_track_l": 2500, "m_track_r": 2500, "m_carbody": 2500, "m_hubs": 200,
    "m_house": 2000, "m_counterweight": 4000, "m_deck": 800, "m_cab": 500, "m_tank": 400,
    "m_boom": 1600, "m_stick": 800, "m_bucket": 700,
}

YELLOW, DARK, RUBBER, SEAT, CHROME, GLASS, LENS, BEACON = range(8)
LOGO, STRIPE, LETTERS, HAZARD, BADGE = range(8, 13)     # livery decals (crawler.decal_materials)


def materials():
    glass = bpy.data.materials.new("cab_glass")
    glass.use_nodes = True
    bsdf = glass.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.25, 0.3, 0.35, 1.0)
    bsdf.inputs["Alpha"].default_value = 0.35
    glass.blend_method = "BLEND"
    glass.a3ob_properties_material.texture_type = "CUSTOM"
    glass.a3ob_properties_material.color_raw = "#(argb,8,8,3)color(0.25,0.30,0.35,0.35,ca)"
    return [
        rv.color_material("paint_yellow", (0.80, 0.55, 0.08), 0.55, 0.3),
        rv.color_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7),
        rv.color_material("track_steel", (0.10, 0.09, 0.08), 0.8, 0.6),
        rv.color_material("seat_vinyl", (0.06, 0.06, 0.06), 0.7, 0.0),
        rv.color_material("cylinder_chrome", (0.70, 0.70, 0.72), 0.25, 1.0),
        glass,
        *crawler.detail_materials(),
        *crawler.decal_materials("bm_badge_exc_ca"),
    ]


def beam(b, a, c, ha, hc, half_w, mat, groups):
    """A straight member from (y, z) a to c, ha thick at a and hc at c, half_w either side of x = 0"""
    d = (c[0] - a[0], c[1] - a[1])
    n = math.hypot(*d)
    perp = (-d[1] / n, d[0] / n)
    quad = [(a[0] - perp[0] * ha / 2, a[1] - perp[1] * ha / 2), (c[0] - perp[0] * hc / 2, c[1] - perp[1] * hc / 2),
            (c[0] + perp[0] * hc / 2, c[1] + perp[1] * hc / 2), (a[0] + perp[0] * ha / 2, a[1] + perp[1] * ha / 2)]
    b.prism_x(quad, -half_w, half_w, mat, groups)


def counterweight_outline():
    """(x, y) outline of the counterweight: an arc of the tail swing radius at the back"""
    pts = []
    for i in range(9):
        a = math.radians(238 + (302 - 238) * i / 8)
        pts.append((TAIL_R * math.cos(a), TAIL_R * math.sin(a)))
    return pts + [(pts[-1][0], -1.6), (pts[0][0], -1.6)]


def facing_in(points):
    """(y, z) points mirrored about the bucket pin: drawn facing out, a bucket faces in"""
    return [(2 * BUCKET_PIN[0] - y, z) for y, z in points]


# The bucket's back plate, from its top behind the pin down round to the teeth, which point
# back towards the machine (a backhoe bucket)
BUCKET_OUTER = facing_in([(5.95, 1.45), (5.88, 0.85), (6.0, 0.45), (6.3, 0.22), (6.75, 0.22), (7.1, 0.42)])


def bucket_shell():
    """Closed (y, z) profile of the bucket's curved back plate, 6 cm thick, open to the machine"""
    inner = []
    for (y, z) in BUCKET_OUTER:
        inner.append((y - 0.05, z + 0.05))
    return BUCKET_OUTER + list(reversed(inner))


def build_visual(mats):
    b = MeshBuilder()

    # Lower: tracks, car body, cross beams, slewing ring
    TRACKS.visual(b, RUBBER, DARK, bottom_rollers=5, groups=UNDER)
    b.box_between((-0.7, -0.9, 0.40), (0.7, 0.9, 0.95), DARK, UNDER)
    b.box_between((-1.0, -0.4, 0.5), (1.0, 0.4, 0.8), DARK, UNDER)
    b.cylinder(0.85, 0.12, (0, 0, 1.01), DARK, UNDER, segments=24)

    S = ()      # the house: the model's root
    # House: deck, engine cover, counterweight, exhaust
    b.box_between((-1.25, -1.6, DECK_Z), (1.25, 1.25, FLOOR_Z), YELLOW, S)
    b.box_between((-1.25, -1.6, FLOOR_Z), (1.25, CAB[1], 2.1), YELLOW, S)
    b.prism_z(counterweight_outline(), DECK_Z, 2.1, YELLOW, S)
    house_details(b, S)
    # Cab, front left: lower panels, glass, corner posts, roof
    x0, y0, x1, y1 = CAB
    # lower panels: a shell round the seat and the driver's legs, on a floor plate
    w = 0.04
    b.box_between((x0, y0, FLOOR_Z), (x0 + w, y1, 1.8), YELLOW, S)
    b.box_between((x1 - w, y0, FLOOR_Z), (x1, y1, 1.8), YELLOW, S)
    b.box_between((x0 + w, y0, FLOOR_Z), (x1 - w, y0 + w, 1.8), YELLOW, S)
    b.box_between((x0 + w, y1 - w, FLOOR_Z), (x1 - w, y1, 1.8), YELLOW, S)
    b.box_between((x0 + w, y0 + w, FLOOR_Z), (x1 - w, y1 - w, FLOOR_Z + 0.02), DARK, S)
    b.box_between((x0 + 0.03, y0 + 0.03, 1.8), (x1 - 0.03, y1 - 0.03, 2.85), GLASS, S)
    for x in (x0 + 0.04, x1 - 0.04):
        for y in (y0 + 0.04, y1 - 0.04):
            b.box_between((x - 0.04, y - 0.04, 1.8), (x + 0.04, y + 0.04, 2.85), YELLOW, S)
    b.box_between((x0 - 0.02, y0 - 0.02, 2.85), (x1 + 0.02, y1 + 0.02, 2.95), YELLOW, S)
    # Inside: seat, console, two joysticks
    b.box_between((-1.0, -0.2, FLOOR_Z), (-0.55, 0.25, 1.69), SEAT, S)
    b.box_between((-1.0, -0.3, 1.69), (-0.55, -0.2, 2.3), SEAT, S)
    b.box_between((-1.15, 0.75, FLOOR_Z), (-0.4, 0.95, 1.75), DARK, S)
    for x in (-1.1, -0.45):
        b.box_between((x - 0.06, -0.2, FLOOR_Z), (x + 0.06, 0.3, 1.6), DARK, S)
        b.rod((x, 0.2, 1.6), (x, 0.25, 1.85), 0.02, DARK, S)
        b.cylinder(0.03, 0.08, (x, 0.25, 1.88), RUBBER, S, segments=8)
    # Right front: hydraulic and fuel tanks; boom foot cheeks
    b.box_between((0.30, CAB[1], FLOOR_Z), (1.25, 1.2, 2.0), YELLOW, S)
    for x in (-0.28, 0.22):
        b.box_between((x, 0.6, FLOOR_Z), (x + 0.06, 1.3, 1.95), DARK, S)

    # Boom: two straight members meeting at the knee
    beam(b, BOOM_FOOT, BOOM_KNEE, 0.55, 0.7, 0.25, YELLOW, "boom")
    beam(b, BOOM_KNEE, BOOM_TIP, 0.7, 0.45, 0.25, YELLOW, "boom")
    b.cylinder(0.12, 0.62, (0, *BOOM_FOOT), DARK, "boom", segments=12, rot=X_AXIS_ROT)
    b.cylinder(0.11, 0.6, (0, *BOOM_TIP), DARK, "boom", segments=12, rot=X_AXIS_ROT)
    b.box_between((-0.12, STICK_CYL[0][0] - 0.15, 3.2), (0.12, STICK_CYL[0][0] + 0.15, STICK_CYL[0][1]), DARK,
                  "boom")   # stick cylinder bracket
    # Stick: lever top, stick pivot, bucket pivot
    beam(b, STICK_TOP, BUCKET_PIN, 0.45, 0.32, 0.19, YELLOW, "stick")
    b.cylinder(0.1, 0.46, (0, *BUCKET_PIN), DARK, "stick", segments=12, rot=X_AXIS_ROT)
    # Bucket: curved back plate, side plates, teeth
    b.prism_x(bucket_shell(), -0.5, 0.5, DARK, "bucket")
    for side in (-1, 1):
        x0b, x1b = sorted((side * 0.5, side * 0.54))
        b.prism_x(BUCKET_OUTER + [(BUCKET_PIN[0], 1.45)], x0b, x1b, YELLOW, "bucket")
    for i in range(5):
        x = -0.4 + 0.2 * i
        b.box_between((x - 0.04, 5.15, 0.36), (x + 0.04, 5.35, 0.44), DARK, "bucket")
    # lug for the bucket cylinder, on top of the bucket; bracket for its base on the stick
    b.box_between((-0.07, BUCKET_CYL[1][0] - 0.1, 1.4), (0.07, BUCKET_CYL[1][0] + 0.06, 1.56), DARK, "bucket")
    b.box_between((-0.07, 5.72, BUCKET_CYL[0][1] - 0.12), (0.07, BUCKET_CYL[0][0] + 0.04, BUCKET_CYL[0][1] + 0.08),
                  DARK, "stick")

    # Cylinders: boom (two, either side of the boom), stick (on top), bucket (on the stick's
    # outer face). Barrel + rod cover the longest stroke (see the rod offsets printed below)
    for x in (-0.36, 0.36):
        crawler.cylinder(b, x, *BOOM_CYL, 0.95, 1.35, DARK, CHROME, "boom_cyl", "boom_rod", barrel_r=0.09,
                         rod_r=0.05)
    crawler.cylinder(b, 0.0, *STICK_CYL, 1.45, 1.95, DARK, CHROME, "stick_cyl", "stick_rod", barrel_r=0.09,
                     rod_r=0.05)
    crawler.cylinder(b, 0.0, *BUCKET_CYL, 1.4, 1.5, DARK, CHROME, "bucket_cyl", "bucket_rod")

    arm_livery(b)
    return b.to_object("Excavator_LOD1", mats)


HOUSE_TOP = 2.1
HOOD_Y = (-1.6, CAB[1])             # engine housing: between the counterweight and the cab


def side_walls(b, S):
    """The house's left and right faces, s running front to back on the left (as seen from
    outside) and back to front on the right"""
    left = rv.Wall(b, (-1.25, 0, 0), (0, -1, 0), (0, 0, 1), S)
    right = rv.Wall(b, (1.25, 0, 0), (0, 1, 0), (0, 0, 1), S)
    return left, right


def house_details(b, S):
    """Engine hood, access doors, grilles, exhaust, rails, lights and the house's livery"""
    y0, y1 = HOOD_Y
    # Hood (seen from above, front up): engine hatch with a louvred grille, a second hatch,
    # air cleaner, muffler and exhaust stack
    top = rv.Wall(b, (0, 0, HOUSE_TOP), (1, 0, 0), (0, 1, 0), S)
    top.door(-1.05, -1.5, 0.45, -0.55, DARK, hinge="top")
    top.grille(-0.95, -1.35, 0.3, -0.72, DARK, YELLOW)
    top.seams(0.55, -1.5, 1.15, -0.55, DARK)
    b.cylinder(0.09, 0.22, (0.85, -0.75, HOUSE_TOP + 0.11), DARK, S, segments=14)
    b.cylinder(0.1, 0.06, (0.85, -0.75, HOUSE_TOP + 0.25), DARK, S, segments=14, radius2=0.05)
    b.box_between((0.62, -1.2, HOUSE_TOP), (0.98, -0.88, HOUSE_TOP + 0.14), DARK, S)
    b.cylinder(0.055, 0.5, (0.75, -1.03, HOUSE_TOP + 0.38), DARK, S, segments=10)
    b.cylinder(0.08, 0.26, (0.75, -1.03, HOUSE_TOP + 0.33), DARK, S, segments=10)
    b.cylinder(0.075, 0.012, (0.75, -1.01, HOUSE_TOP + 0.65), DARK, S, segments=10,
               rot=Matrix.Rotation(math.radians(25), 4, "X"))                  # rain cap
    # Handrail along the right edge of the hood and the tank
    for y in (-1.45, -0.5, 0.45, 1.1):
        z = HOUSE_TOP if y < CAB[1] else 2.0
        b.rod((1.18, y, z), (1.18, y, 2.45), 0.018, YELLOW, S)
    b.rod((1.18, -1.45, 2.45), (1.18, 1.1, 2.45), 0.018, YELLOW, S)

    left, right = side_walls(b, S)
    zd0, zd1 = FLOOR_Z + 0.08, HOUSE_TOP - 0.1
    # Left, behind the cab: two doors, the rear one over the engine's air intake
    l0, l1 = -y1, -y0                   # s range of the engine housing on the left
    left.door(l0 + 0.05, zd0, l0 + 0.5, zd1, DARK, hinge="left")
    left.door(l0 + 0.55, zd0, l1 - 0.05, zd1, DARK, hinge="right")
    left.grille(l0 + 0.65, zd0 + 0.15, l1 - 0.2, zd1 - 0.15, DARK, YELLOW)
    # Right: the radiator behind a mesh door at the back, a pump door, the tank's toolbox
    right.door(y0 + 0.05, zd0, y0 + 0.62, zd1, DARK, hinge="left")
    right.mesh(y0 + 0.13, zd0 + 0.12, y0 + 0.54, zd1 - 0.12, DARK, YELLOW)
    right.door(y0 + 0.67, zd0, y1 - 0.05, zd1, DARK, hinge="right")
    right.door(y1 + 0.1, zd0, y1 + 0.75, 1.75, DARK, hinge="top")
    right.plate(y1 + 1.0, 1.4, y1 + 1.06, 1.8, 0.02, DARK)              # hydraulic oil sight gauge
    right.decal(y1 + 1.25, 1.88, 0.5, 0.125, BADGE)
    b.cylinder(0.06, 0.05, (0.95, 0.95, 2.02), DARK, S, segments=12)   # fuel cap
    # Livery: a black band with a red pinstripe along both sides under the hood line
    band = (0.3, 0.06, 1.0, 0.3)
    left.decal((l0 + l1) / 2, HOUSE_TOP - 0.045, l1 - l0, 0.05, STRIPE, uv=band)
    right.decal((y0 + y1) / 2, HOUSE_TOP - 0.045, y1 - y0, 0.05, STRIPE, uv=band)

    # Grab handle up the tank's front right corner (steps would hang over the track)
    b.rod((1.2, 1.24, 1.4), (1.2, 1.24, 1.95), 0.016, DARK, S)
    for z in (1.4, 1.95):
        b.rod((1.2, 1.2, z), (1.2, 1.26, z), 0.014, DARK, S)
    # Front: the logo plate on the tank; work lights under the cab roof; a beacon on it
    front = rv.Wall(b, (0, 1.2, 0), (-1, 0, 0), (0, 0, 1), S)
    front.decal(-0.78, 1.7, 0.5, 0.25, LOGO)
    cab_front = rv.Wall(b, (0, CAB[3] + 0.02, 0), (-1, 0, 0), (0, 0, 1), S)
    for s in (0.45, 1.1):
        cab_front.light(s, 2.88, 0.06, LENS, DARK, depth=0.06)
    b.cylinder(0.07, 0.12, (-0.4, -0.2, 3.01), BEACON, S, segments=12)
    # Cab: a wiper along the bottom of the front glass, the door handle and a mirror on the left
    b.rod((-1.0, CAB[3] + 0.005, 1.84), (-0.62, CAB[3] + 0.005, 1.95), 0.008, DARK, S)   # parked low
    b.box_between((CAB[0] - 0.03, 0.55, 1.95), (CAB[0], 0.7, 1.98), DARK, S)
    b.rod((CAB[0], 1.1, 2.6), (CAB[0] - 0.25, 1.25, 2.7), 0.015, DARK, S)
    b.box_between((CAB[0] - 0.3, 1.22, 2.55), (CAB[0] - 0.22, 1.27, 2.8), DARK, S)

    # Counterweight: FAT across the back, hazard stripes at its corners, two lamps on top.
    # The outline's arc runs from the left corner to the right: left to right seen from behind.
    arc = counterweight_outline()[:9]
    b.decal_strip(arc[2:7], 1.38, 1.88, 0.004, LETTERS, S)
    b.decal_strip(arc[0:3], 1.12, 1.3, 0.004, HAZARD, S, uv=(0, 0, 1, 0.4))
    b.decal_strip(arc[6:9], 1.12, 1.3, 0.004, HAZARD, S, uv=(0, 0, 1, 0.4))
    for i in (1, 7):
        x, y = arc[i]
        b.cylinder(0.05, 0.05, (x * 0.95, y * 0.95, HOUSE_TOP + 0.025), LENS, S, segments=10)


def member_wall(b, a, c, x, frac, groups):
    """The outward side face of an arm member from (y, z) a to c, at x, centred `frac`
    of the way along; s runs along the member (towards the tip on the right, away from it
    on the left, so text reads from outside), t up"""
    d = (c[0] - a[0], c[1] - a[1])
    n = math.hypot(*d)
    along = (0, d[0] / n, d[1] / n)
    up = (0, -along[2], along[1])
    if up[2] < 0:
        up = (0, -up[1], -up[2])
    right = along if x > 0 else tuple(-v for v in along)
    mid = (x, a[0] + d[0] * frac, a[1] + d[1] * frac)
    wall = rv.Wall(b, mid, right, up, groups)
    if wall.n.x * x < 0:        # facing inwards: turn it round
        wall = rv.Wall(b, mid, tuple(-v for v in right), up, groups)
    return wall


def arm_livery(b):
    """FAT stripes down both sides of the boom, the model number on the stick, a work light"""
    for side in (-1, 1):
        member_wall(b, BOOM_FOOT, BOOM_KNEE, side * 0.25, 0.5, "boom").decal(0, 0, 2.0, 0.25, STRIPE)
        member_wall(b, STICK_TOP, BUCKET_PIN, side * 0.19, 0.55, "stick").decal(0, 0, 0.8, 0.2, BADGE)
    lamp = rv.Wall(b, (0, BOOM_KNEE[0] - 0.3, BOOM_KNEE[1] + 0.36), (-1, 0, 0), (0, 0, 1), "boom")
    lamp.light(0, 0.0, 0.07, LENS, DARK)


def collision_parts(kind):
    """Convex boxes for a collision LOD. kind: geometry, or fire (fire and view geometry:
    damage zone selections and the seat)."""
    dmg = kind == "fire"

    def parts(b, comp):
        def zone(name):
            return [name] if dmg else []

        b.box_between((-0.7, -0.9, 0.40), (0.7, 0.9, 1.07), 0, comp("m_carbody", *UNDER, *zone("dmgZone_chassis")))
        TRACKS.collision(b, comp, extra=(*UNDER, *zone("dmgZone_chassis")))
        b.box_between((-1.25, -1.6, DECK_Z), (1.25, CAB[1], 2.1), 0, comp("m_house", *zone("dmgZone_engine")))
        b.prism_z(counterweight_outline(), DECK_Z, 2.1, 0, comp("m_counterweight", *zone("dmgZone_chassis")))
        b.box_between((-1.25, CAB[1], DECK_Z), (1.25, 1.25, FLOOR_Z), 0, comp("m_deck", *zone("dmgZone_chassis")))
        # The cab is also the get-in action's target (Crew Driver actionSel = "seat_driver"):
        # from outside you aim at the cab, like at a car door
        b.box_between((CAB[0], CAB[1], FLOOR_Z), (CAB[2], CAB[3], 2.95), 0,
                      comp("m_cab", *zone("dmgZone_chassis"), *(["seat_driver"] if dmg else [])))
        b.box_between((0.30, CAB[1], FLOOR_Z), (1.25, 1.2, 2.0), 0, comp("m_tank", *zone("dmgZone_fueltank")))
        beam(b, BOOM_FOOT, BOOM_KNEE, 0.55, 0.7, 0.25, 0, comp("m_boom", "boom", *zone("dmgZone_arm")))
        beam(b, BOOM_KNEE, BOOM_TIP, 0.7, 0.45, 0.25, 0, comp("m_boom", "boom", *zone("dmgZone_arm")))
        beam(b, STICK_TOP, BUCKET_PIN, 0.45, 0.32, 0.19, 0, comp("m_stick", "stick", *zone("dmgZone_arm")))
        b.prism_x(facing_in([(5.95, 1.45), (5.88, 0.85), (6.3, 0.22), (6.75, 0.22), (7.25, 0.42)]), -0.54, 0.54, 0,
                  comp("m_bucket", "bucket", *zone("dmgZone_arm")))
        if kind == "geometry":
            TRACKS.hubs(b, comp)

    return parts


def memory_points():
    pts = {}
    TRACKS.memory_points(pts)

    def axis_x(point):
        return [(-0.6, *point), (0.6, *point)]

    pts["undercarriage_axis"] = [(0, 0, 0.9), (0, 0, 1.6)]
    pts["boom_axis"] = axis_x(BOOM_FOOT)
    pts["boom_cyl_axis"] = axis_x(BOOM_CYL[0])
    pts["stick_axis"] = axis_x(BOOM_TIP)
    pts["stick_cyl_axis"] = axis_x(STICK_CYL[0])
    pts["bucket_axis"] = axis_x(BUCKET_PIN)
    pts["bucket_cyl_axis"] = axis_x(BUCKET_CYL[0])
    for name, (base, mount) in (("boom", BOOM_CYL), ("stick", STICK_CYL), ("bucket", BUCKET_CYL)):
        pts[name + "_rod_axis"] = [(0, *p) for p in crawler.cylinder_rod_axis(base, mount)]
    # Getting in from the left, beside the track (stand within 1 m of seat_con_1_1)
    pts["pos_driver"] = (-2.1, 0.3, 0.0)
    pts["pos_driver_dir"] = (-1.6, 0.3, 0.0)
    pts["seat_con_1_1"] = (-1.95, 0.3, 0.3)
    pts["crewDriver"] = CREW_POS
    pts["ptcexhaust_start"] = (0.75, -1.0, 2.62)
    pts["ptcexhaust_end"] = (0.75, -1.0, 2.8)
    pts["ptcenginepos"] = (0.0, -1.0, 2.1)
    pts["ptccoolantpos"] = (0.0, -1.3, 2.0)
    pts["pos_carhorn"] = (0.0, 0.8, 1.5)
    pts["dmgZone_engine"] = (0.0, -1.0, 1.6)
    pts["dmgZone_fueltank"] = (0.8, 0.4, 1.6)
    pts["dmgZone_arm"] = (0.0, 3.5, 3.0)
    pts["ce_center"] = (0.0, 1.5, 1.5)
    pts["ce_radius"] = (0.0, 1.5, 7.5)
    return pts


def report_model_cfg():
    """The numbers model.cfg and config.cpp need, from the constants above"""
    for name, (a0, a1, speed) in JOINTS.items():
        print(f"[excavator] {name}: angle0 rad {a0} angle1 rad {a1}, initPhase {-a0 / (a1 - a0):.4f}, "
              f"animPeriod {1 / speed:.1f}")
    for cyl, (pivot, (base, mount), joint) in {
        "boom_cyl": (BOOM_FOOT, BOOM_CYL, "boom"),
        "stick_cyl": (BOOM_TIP, STICK_CYL, "stick"),
        "bucket_cyl": (BUCKET_PIN, BUCKET_CYL, "bucket"),
    }.items():
        j0, j1, _ = JOINTS[joint]
        a0, a1 = crawler.cylinder_swing(pivot, base, mount, j0, j1)
        e0, e1 = (crawler.cylinder_extension(pivot, base, mount, a) for a in (j0, j1))
        print(f"[excavator] {cyl.replace('_cyl', '_rod')}: offset0 {e0:.3f} offset1 {e1:.3f}")
        print(f"[excavator] {cyl}: angle0 rad {a0:.2f} angle1 rad {a1:.2f}")


def main():
    rv.enable_addon()
    TRACKS.build_roller(os.path.join(MODEL_DIR, "proxy", "bm_exc_roller.p3d"))

    rv.reset_scene()
    visual = build_visual(materials())
    geometry = crawler.collision_object("Excavator_Geometry", collision_parts("geometry"), MASSES)
    fire = crawler.collision_object("Excavator_Fire", collision_parts("fire"))
    view = crawler.collision_object("Excavator_View", collision_parts("fire"))
    print(f"[excavator] mass {sum(MASSES.values())} kg")
    report_model_cfg()
    crawler.assemble("excavator", visual, geometry, fire, view, memory_points(), TRACKS, CREW_POS, BATTERY_POS,
                     os.path.join(MODEL_DIR, "bm_excavator.p3d"), battery_groups=UNDER,
                     preview=((0, 2.0, 1.6), (8.5, 9.5, 5.5)))


main()
