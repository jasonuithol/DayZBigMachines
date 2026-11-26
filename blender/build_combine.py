"""Procedurally builds the combine harvester for the BigMachines mod: the map's
Land_Wreck_Harverster (an old Soviet-era combine, pale green with a white grain tank; reference
shots in data/reference/combine_wreck_*.png) restored.

Run headless from the project root:
    blender --background --python blender/build_combine.py

Outputs:
    BigMachines/combine/bm_combine.p3d                      the machine (MLOD)
    BigMachines/combine/proxy/bm_combine_wheel_front.p3d    the big drive wheels' item
    BigMachines/combine/proxy/bm_combine_wheel_rear.p3d     the small steering wheels' item
    models/combine.blend, models/combine_preview.png

It drives on four real wheels (blender/wheeled.py): big drive wheels at the front, small
steering wheels at the back. Moving parts, each a bone (BigMachines/model.cfg):
    feeder      the feeder house, swinging about its top end on the body: lifts the header
    header      child of feeder: the cutting platform (cutter bar, side plates, auger)
    reel        child of header: the reel, spinning while the header runs
    header_auger  child of header: the cross auger inside the platform, spinning with it
    auger       the unloading auger, swinging out to the left about its foot
Coordinates: see rv.py (Blender X right, Y forward, Z up; origin on the ground, centred).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawler  # noqa: E402
import rv  # noqa: E402
import wheeled  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from rv import MeshBuilder, X_AXIS_ROT  # noqa: E402

MODEL_DIR = os.path.join(crawler.ROOT, "BigMachines", "combine")
FRONT_WHEEL = "BigMachines\\combine\\proxy\\bm_combine_wheel_front.p3d"
REAR_WHEEL = "BigMachines\\combine\\proxy\\bm_combine_wheel_rear.p3d"
WHEELS = wheeled.Wheels([
    wheeled.Axle(1, y=1.0, x=1.42, radius=0.78, width=0.52, wheel_path=FRONT_WHEEL, travel_up=0.08, travel_down=0.08),
    wheeled.Axle(2, y=-3.0, x=1.22, radius=0.46, width=0.30, wheel_path=REAR_WHEEL, travel_up=0.12, travel_down=0.12),
])
BATTERY_POS = (0.75, -2.3, 1.15)    # behind a side panel at the back right

# --- Body ---
BODY_X = 1.12                       # lower body, between the drive wheels
BODY_Y = (-3.9, 1.9)
BODY_Z = (0.85, 2.55)
REAR_X = 0.98                       # narrower at the back, between the steering wheels
TANK = (-1.38, -1.7, 1.38, 1.2, 2.55, 3.55)    # grain tank: x0, y0, x1, y1, z0, z1 (white)
HOOD = (-1.12, -3.9, 1.12, -1.7, 2.55, 3.2)     # engine housing behind the tank (white)
DECK_Z = 2.3                        # the platform in front of the tank; the cab stands on it
DECK = (-1.35, 1.2, 0.95, 2.75)     # x0, y0, x1, y1
CAB = (-1.05, 1.3, 0.55, 2.55)      # x0, y0, x1, y1
CAB_TOP = 3.95
CREW_POS = (-0.25, 1.75, 2.78)      # driver's seat proxy, on the cushion

# --- Header ---
FEEDER_PIVOT = (1.75, 1.55)         # (y, z): the feeder house's top end, on the body
FEEDER_FRONT = (3.15, 0.75)         # (y, z): its front end, where the header hangs
FEEDER_HALF_W = 0.62
HEADER_HALF_W = 3.0                 # 6 m cutting width (the wreck's is 7.8: too wide for DayZ's roads)
HEADER_Y = (2.95, 4.75)             # back wall to cutter bar
HEADER_Z = 0.12                     # the platform's floor, header down (phase 0)
HEADER_LIFT = 0.3                   # m the header's and feeder's physics sit above their visual bottom
REEL_C = (4.25, 1.3)                # (y, z): the reel's axle
REEL_R = 0.55
AUGER_C = (3.45, 0.45)              # (y, z): the cross auger in the platform
# Joints: (angle at phase 0, at phase 1, speed). The feeder swings up about FEEDER_PIVOT: phase
# 0 = header on the ground (as modelled), 1 = raised for driving (+ = front up). The unloading
# auger swings out about its foot: 0 = folded along the left side (as modelled), 1 = out.
JOINTS = {
    "header": (0, 14, 0.30),
    "auger": (0, 95, 0.12),
}
AUGER_FOOT = (-0.85, 0.7, 3.8)      # x, y, z: its swivel, on the tank roof's front left
AUGER_SLOPE = 0.7                   # rise per metre along the machine (~35 deg)
AUGER_TOP = (-0.85, -1.7, 3.8 + 2.4 * AUGER_SLOPE)     # its spout end, folded back over the tank
AUGER_REST_Y = -1.3                 # where it rests in its cradle
AUGER_R = 0.16

MASSES = {
    "m_body": 3600, "m_rear": 700, "m_tank": 1100, "m_hood": 1300, "m_deck": 250, "m_cab": 350,
    "m_feeder": 450, "m_header": 1000, "m_hubs": 200,
}

GREEN, WHITE, DARK, RUBBER, SEAT, GLASS, LENS, BEACON, TAIL = range(9)
LOGO, STRIPE, LETTERS, HAZARD, BADGE = range(9, 14)     # crawler.decal_materials (only HAZARD used)

TANK_GREEN = (0.44, 0.63, 0.48)
CREAM = (0.84, 0.81, 0.73)


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
        rv.weathered_material("paint_mint", TANK_GREEN, 0.6, 0.2),
        rv.weathered_material("paint_cream", CREAM, 0.6, 0.2),
        rv.weathered_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7),
        rv.color_material("rubber", (0.04, 0.04, 0.04), 0.9, 0.0),
        rv.color_material("seat_vinyl", (0.06, 0.06, 0.06), 0.7, 0.0),
        glass,
        *crawler.detail_materials(),
        rv.color_material("tail_lens", (0.7, 0.05, 0.04), 0.15, 0.0),
        *crawler.decal_materials("bm_badge_exc_ca"),
    ]


def feeder_quad():
    """(y, z) outline of the feeder house's side: from its top end on the body down to the header"""
    (py, pz), (fy, fz) = FEEDER_PIVOT, FEEDER_FRONT
    return [(py - 0.15, pz + 0.35), (py - 0.15, pz - 0.35), (fy, fz - 0.4), (fy, fz + 0.35)]


def header_side():
    """(y, z) outline of the header's end plates: a wedge, high at the back wall"""
    y0, y1 = HEADER_Y
    z = HEADER_Z
    return [(y0, z), (y1 + 0.05, z), (y1 - 0.35, z + 0.45), (y0 + 0.45, 1.15), (y0, 1.15)]


def header_parts(b, mat, frame_mat, groups):
    """The cutting platform: floor, back wall with its top rail, end plates, crop dividers
    pointing forward at each end, skid shoes, cutter bar with its guards, and the reel's arms
    and lift cylinders"""
    y0, y1 = HEADER_Y
    z = HEADER_Z
    h = HEADER_HALF_W
    b.box_between((-h, y0, z), (h, y1 - 0.1, z + 0.06), mat, groups)                    # floor
    b.box_between((-h, y0 - 0.06, z), (h, y0, 1.15), mat, groups)                        # back wall
    b.box_between((-h, y0 - 0.1, 1.1), (h, y0 + 0.04, 1.2), frame_mat, groups)          # its top rail
    for k in range(7):                                                                   # stiffeners
        x = -h + 0.3 + k * (2 * h - 0.6) / 6
        b.box_between((x - 0.03, y0 - 0.12, z + 0.05), (x + 0.03, y0 - 0.06, 1.1), mat, groups)
    for side in (-1, 1):
        x0, x1 = sorted((side * h, side * (h - 0.04)))
        b.prism_x(header_side(), x0, x1, mat, groups)                                    # end plate
        # crop divider: a pointed nose out in front of the end plate
        xa, xb = sorted((side * (h - 0.02), side * (h + 0.06)))
        b.prism_x([(y1 - 0.3, z), (y1 + 0.75, z + 0.08), (y1 - 0.3, z + 0.55)], xa, xb, WHITE, groups)
        # hazard stripes on the end plate, seen from outside
        end = rv.Wall(b, (side * (h + 0.004), 0, 0), (0, side, 0), (0, 0, 1), groups)
        end.decal(side * (y0 + 0.55), 0.62, 0.6, 0.3, HAZARD, uv=(0, 0, 1, 0.5))
    for x in (-h + 0.5, -1.0, 1.0, h - 0.5):                                             # skid shoes
        b.prism_x([(y0 + 0.2, z - 0.06), (y1 - 0.3, z - 0.06), (y1 - 0.15, z), (y0 + 0.2, z)], x - 0.06, x + 0.06,
                  frame_mat, groups)
    b.box_between((-h, y1 - 0.12, z - 0.02), (h, y1 + 0.05, z + 0.05), frame_mat, groups)  # cutter bar
    for k in range(int(2 * h / 0.15)):
        x = -h + 0.075 + 0.15 * k
        b.prism_x([(y1 + 0.02, z), (y1 + 0.16, z + 0.015), (y1 + 0.02, z + 0.04)], x - 0.02, x + 0.02, frame_mat,
                  groups)
    # reel arms: from the back of each end plate up and forward to the reel's axle; a lift
    # cylinder under each
    for side in (-1, 1):
        x = side * (h - 0.12)
        b.rod((x, y0 + 0.1, 1.15), (x, REEL_C[0] + 0.1, REEL_C[1] + 0.05), 0.04, mat, groups)
        b.rod((x, y0 + 0.05, 0.75), (x, (y0 + REEL_C[0]) / 2 + 0.2, 1.22), 0.03, frame_mat, groups)
        b.rod((x, y0 + 0.05, 0.75), (x, y0 + 0.35, 0.92), 0.045, mat, groups)


def reel(b, mat, frame_mat, groups):
    """Six bats on four spiders, about the reel's axle (x), with spring tines"""
    h = HEADER_HALF_W - 0.2
    cy, cz = REEL_C
    b.cylinder(0.05, 2 * h + 0.3, (0, cy, cz), frame_mat, groups, segments=8, rot=X_AXIS_ROT)
    for x in (-h + 0.05, -h / 3, h / 3, h - 0.05):
        b.cylinder(0.09, 0.06, (x, cy, cz), frame_mat, groups, segments=8, rot=X_AXIS_ROT)
        for k in range(6):
            a = 2 * math.pi * k / 6
            b.rod((x, cy, cz), (x, cy + REEL_R * math.cos(a), cz + REEL_R * math.sin(a)), 0.018, frame_mat, groups,
                  segments=6)
    for k in range(6):
        a = 2 * math.pi * k / 6
        y, z = cy + REEL_R * math.cos(a), cz + REEL_R * math.sin(a)
        b.box_between((-h, y - 0.035, z - 0.025), (h, y + 0.035, z + 0.025), mat, groups)
        for t in range(int(2 * h / 0.25)):                                           # tines
            x = -h + 0.12 + 0.25 * t
            b.rod((x, y, z), (x, y + 0.2 * math.sin(a), z - 0.2 * math.cos(a)), 0.006, frame_mat, groups,
                  segments=4)


def header_auger(b, mat, frame_mat, groups):
    """The cross auger: a tube with flights winding in from both ends to the middle, and
    retracting fingers there to feed the feeder house"""
    h = HEADER_HALF_W - 0.1
    cy, cz = AUGER_C
    b.cylinder(0.16, 2 * h, (0, cy, cz), mat, groups, segments=12, rot=X_AXIS_ROT)
    for side in (-1, 1):
        for k in range(16):
            x = side * (h - 0.1 - k * 0.16)
            if abs(x) < 0.55:
                continue
            a = side * k * 0.9
            b.box((0.025, 0.5, 0.05), (x, cy, cz), frame_mat, groups, rot=Matrix.Rotation(a, 4, "X"))
    for k in range(6):
        a = 2 * math.pi * k / 6
        for x in (-0.35, 0.0, 0.35):
            b.rod((x, cy, cz), (x, cy + 0.3 * math.cos(a), cz + 0.3 * math.sin(a)), 0.012, frame_mat, groups,
                  segments=4)


def unloading_auger(b, mat, frame_mat, groups):
    """The tube, its spout turned down at the far end, the swivel at its foot, a joint flange
    halfway and a strap where it lies in its cradle"""
    foot, top = Vector(AUGER_FOOT), Vector(AUGER_TOP)
    d = (top - foot).normalized()
    b.rod(foot, top, AUGER_R, mat, groups, segments=12)
    b.rod(top - d * 0.05, top + Vector((0, 0, -0.45)), AUGER_R * 0.8, mat, groups, segments=10)    # spout
    b.cylinder(AUGER_R * 0.85, 0.12, top + Vector((0, 0, -0.5)), frame_mat, groups, segments=10)
    b.cylinder(AUGER_R + 0.08, 0.3, foot, frame_mat, groups, segments=12)                            # swivel
    mid = (foot + top) / 2
    b.rod(mid - d * 0.03, mid + d * 0.03, AUGER_R + 0.035, frame_mat, groups, segments=12)          # flange
    for f in (0.25, 0.75):
        p = foot + (top - foot) * f
        b.rod(p - d * 0.04, p + d * 0.04, AUGER_R + 0.02, frame_mat, groups, segments=12)


def fender(b, x0, x1, y, hub_z, r, mat, groups):
    """A mudguard arching over a drive wheel, from just behind to just in front of it"""
    n = 9
    for k in range(n):
        a0 = math.radians(25 + 130 * k / n)
        a1 = math.radians(25 + 130 * (k + 1) / n)
        p0 = (y + r * math.cos(a0), hub_z + r * math.sin(a0))
        p1 = (y + r * math.cos(a1), hub_z + r * math.sin(a1))
        q1 = (y + (r + 0.05) * math.cos(a1), hub_z + (r + 0.05) * math.sin(a1))
        q0 = (y + (r + 0.05) * math.cos(a0), hub_z + (r + 0.05) * math.sin(a0))
        b.prism_x([p0, p1, q1, q0], x0, x1, mat, groups)


def body(b, S):
    """Lower body (green) between and over the wheels, axles, fenders"""
    b.box_between((-BODY_X, -1.7, BODY_Z[0]), (BODY_X, BODY_Y[1], BODY_Z[1]), GREEN, S)
    b.box_between((-REAR_X, BODY_Y[0], 1.05), (REAR_X, -1.7, BODY_Z[1]), GREEN, S)
    b.box_between((-REAR_X - 0.08, -1.75, 1.05), (REAR_X + 0.08, -1.65, BODY_Z[1]), GREEN, S)   # step-in
    front, rear = WHEELS.axles
    # drive axle: a beam across, final drive housings into the wheels
    b.box_between((-1.15, front.y - 0.15, 0.62), (1.15, front.y + 0.15, 0.92), DARK, S)
    for side in (-1, 1):
        b.cylinder(0.24, 0.3, (side * 1.05, front.y, front.hub_z), DARK, S, segments=14, rot=X_AXIS_ROT)
        xa, xb = sorted((side * BODY_X, side * (front.x + front.width / 2 + 0.06)))
        fender(b, xa, xb, front.y, front.hub_z, front.radius + 0.1, GREEN, S)
    # steering axle: a beam on a centre pivot, track rods to the wheels
    b.box_between((-1.02, rear.y - 0.1, rear.hub_z - 0.08), (1.02, rear.y + 0.1, rear.hub_z + 0.08), DARK, S)
    b.box_between((-0.18, rear.y - 0.15, rear.hub_z), (0.18, rear.y + 0.15, 1.08), DARK, S)
    b.rod((-0.95, rear.y + 0.22, rear.hub_z), (0.95, rear.y + 0.22, rear.hub_z), 0.025, DARK, S)
    for side in (-1, 1):
        b.cylinder(0.08, 0.16, (side * 1.0, rear.y, rear.hub_z), DARK, S, segments=10)       # king pins

    # left side, s = -y (front to the left as seen from outside)
    left = rv.Wall(b, (-BODY_X, 0, 0), (0, -1, 0), (0, 0, 1), S)
    right = rv.Wall(b, (BODY_X, 0, 0), (0, 1, 0), (0, 0, 1), S)
    for wall, sgn in ((left, -1), (right, 1)):
        # between the wheels: the threshing drum and cleaning shoe doors
        s0, s1 = (-0.15, 1.55) if sgn < 0 else (-1.55, 0.15)
        wall.door(s0 + 0.05, 1.0, (s0 + s1) / 2 - 0.03, 2.35, DARK, hinge="left")
        wall.door((s0 + s1) / 2 + 0.03, 1.0, s1 - 0.05, 2.35, DARK, hinge="right")
        wall.plate(s0, 2.42, s1, 2.47, 0.02, GREEN)                                           # drip rail
    rr = rv.Wall(b, (REAR_X, 0, 0), (0, 1, 0), (0, 0, 1), S)
    rl = rv.Wall(b, (-REAR_X, 0, 0), (0, -1, 0), (0, 0, 1), S)
    rr.door(-3.75, 1.2, -2.0, 2.4, DARK, hinge="left")                                       # straw walkers
    rr.plate(-2.65, 1.35, -2.15, 1.75, 0.015, DARK)                                           # battery box lid
    rl.door(2.0, 1.2, 3.75, 2.4, DARK, hinge="right")
    # the clean grain elevator up the right side, into the tank
    b.box_between((BODY_X, -0.55, 0.95), (BODY_X + 0.16, -0.25, TANK[5] - 0.25), GREEN, S)
    b.box_between((BODY_X, -0.6, TANK[5] - 0.3), (TANK[2] + 0.02, -0.2, TANK[5] - 0.1), GREEN, S)

    # the back: straw chopper hood hanging under it, tail lights, a hitch
    b.prism_x([(BODY_Y[0], 1.05), (BODY_Y[0], 2.0), (BODY_Y[0] - 0.45, 1.6), (BODY_Y[0] - 0.45, 0.85),
               (BODY_Y[0] + 0.3, 0.85)], -REAR_X + 0.05, REAR_X - 0.05, GREEN, S)
    back = rv.Wall(b, (0, BODY_Y[0], 0), (1, 0, 0), (0, 0, 1), S)
    for s in (-0.75, 0.75):
        back.light(s, 2.25, 0.06, TAIL, DARK, depth=0.05)
    back.light(0.0, 2.25, 0.04, LENS, DARK, depth=0.05)
    back.decal(0, 2.4, 1.4, 0.12, HAZARD, uv=(0, 0, 1, 0.25))
    b.box_between((-0.15, BODY_Y[0] - 0.55, 0.62), (0.15, BODY_Y[0] + 0.1, 0.78), DARK, S)  # hitch


def tank_and_hood(b, S):
    """Grain tank (cream) with chamfered top edges, lids and inspection windows; engine housing
    behind it with louvres, a rotary air screen, exhaust and handrail"""
    x0, y0, x1, y1, z0, z1 = TANK
    c = 0.25
    b.prism_x([(y0, z0), (y1, z0), (y1, z1 - c), (y1 - c, z1), (y0 + c, z1), (y0, z1 - c)], x0, x1, WHITE, S)
    top = rv.Wall(b, (0, 0, z1), (1, 0, 0), (0, 1, 0), S)
    top.door(-0.95, y0 + c + 0.1, -0.05, y1 - c - 0.1, DARK, hinge="top")                      # lids
    top.door(0.05, y0 + c + 0.1, 0.95, y1 - c - 0.1, DARK, hinge="top")
    for wall, sgn in ((rv.Wall(b, (x0, 0, 0), (0, -1, 0), (0, 0, 1), S), -1),
                      (rv.Wall(b, (x1, 0, 0), (0, 1, 0), (0, 0, 1), S), 1)):
        for k in range(3):
            yy = y0 + 0.5 + k * 0.8
            s = -yy if sgn < 0 else yy
            wall.plate(s - 0.12, z1 - c - 0.3, s + 0.12, z1 - c - 0.12, 0.012, GLASS)
            wall.seams(s - 0.15, z1 - c - 0.33, s + 0.15, z1 - c - 0.09, DARK)
        wall.plate(-y1 if sgn < 0 else y0, z0 + 0.02, -y0 if sgn < 0 else y1, z0 + 0.07, 0.025, WHITE)
    hx0, hy0, hx1, hy1, hz0, hz1 = HOOD
    b.prism_x([(hy0, hz0), (hy1, hz0), (hy1, hz1), (hy0 + 0.35, hz1), (hy0, hz1 - 0.35)], hx0, hx1, WHITE, S)
    for wall, sgn in ((rv.Wall(b, (hx0, 0, 0), (0, -1, 0), (0, 0, 1), S), -1),
                      (rv.Wall(b, (hx1, 0, 0), (0, 1, 0), (0, 0, 1), S), 1)):
        a, z = (-hy1 + 0.15, -hy0 - 0.5) if sgn < 0 else (hy0 + 0.5, hy1 - 0.15)
        wall.grille(a, hz0 + 0.1, z, hz1 - 0.1, DARK, WHITE)
    # rotary air screen on top, exhaust behind it, a rail along the right
    b.cylinder(0.42, 0.25, (-0.3, -2.75, hz1 + 0.12), DARK, S, segments=18)
    for k in range(12):
        a = 2 * math.pi * k / 12
        b.rod((-0.3, -2.75, hz1 + 0.26), (-0.3 + 0.4 * math.cos(a), -2.75 + 0.4 * math.sin(a), hz1 + 0.26), 0.012,
              WHITE, S, segments=4)
    b.cylinder(0.07, 0.95, (0.75, -2.05, hz1 + 0.47), DARK, S, segments=10)
    b.cylinder(0.08, 0.01, (0.75, -2.03, hz1 + 0.96), DARK, S, segments=10,
               rot=Matrix.Rotation(math.radians(25), 4, "X"))                                   # rain cap
    for y in (-3.6, -2.4, y0 - 0.05):
        b.rod((hx1 - 0.05, y, hz1), (hx1 - 0.05, y, hz1 + 0.35), 0.015, DARK, S)
    b.rod((hx1 - 0.05, -3.6, hz1 + 0.35), (hx1 - 0.05, y0 - 0.05, hz1 + 0.35), 0.015, DARK, S)
    # the unloading auger's swivel base on the roof, and the cradle it rests in folded: a post
    # up from the roof's back edge with a brace and a saddle
    fx, fy, fz = AUGER_FOOT
    b.cylinder(AUGER_R + 0.12, fz - 0.15 - z1, (fx, fy, (z1 + fz - 0.15) / 2), DARK, S, segments=14)
    ry = AUGER_REST_Y
    rz = fz + (fy - ry) * AUGER_SLOPE - AUGER_R - 0.02          # under the tube there
    b.rod((fx, ry, z1), (fx, ry, rz - 0.04), 0.04, DARK, S)
    b.rod((fx + 0.55, ry, z1), (fx, ry, z1 + 0.75), 0.025, DARK, S)
    b.box_between((fx - 0.14, ry - 0.06, rz - 0.06), (fx + 0.14, ry + 0.06, rz), DARK, S)
    for side in (-1, 1):
        b.box_between((fx + side * 0.14 - 0.02, ry - 0.06, rz - 0.06), (fx + side * 0.14 + 0.02, ry + 0.06, rz + 0.12),
                      DARK, S)


def deck_and_cab(b, S):
    """The platform in front of the tank with its rails and ladder; the cab on it"""
    dx0, dy0, dx1, dy1 = DECK
    b.box_between((dx0, dy0, DECK_Z - 0.06), (dx1, dy1, DECK_Z), DARK, S)
    b.box_between((dx0, dy1 - 0.04, DECK_Z - 0.2), (dx1, dy1, DECK_Z - 0.06), GREEN, S)       # kick plate
    for x, y in ((dx1, dy0 + 0.1), (dx1, dy1 - 0.05), (dx0, dy1 - 0.05), (dx0, 1.3)):
        b.rod((x, y, DECK_Z), (x, y, DECK_Z + 0.95), 0.02, GREEN, S)
    for z in (DECK_Z + 0.5, DECK_Z + 0.95):
        b.rod((dx1, dy0 + 0.1, z), (dx1, dy1 - 0.05, z), 0.02, GREEN, S)
        b.rod((dx0, dy1 - 0.05, z), (dx1, dy1 - 0.05, z), 0.02, GREEN, S)
    lx = dx0 - 0.05
    for y in (1.75, 2.15):
        b.rod((lx - 0.25, y, 0.45), (lx, y, DECK_Z), 0.022, DARK, S)
        b.rod((lx, y, DECK_Z), (lx, y, DECK_Z + 1.0), 0.02, DARK, S)                          # grab rails
    for k in range(7):
        z = 0.55 + k * (DECK_Z - 0.55) / 7
        t = (z - 0.45) / (DECK_Z - 0.45)
        b.box_between((lx - 0.25 * (1 - t) - 0.04, 1.75, z - 0.015), (lx - 0.25 * (1 - t) + 0.04, 2.15, z + 0.015),
                      DARK, S)
    cx0, cy0, cx1, cy1 = CAB
    w = 0.04
    b.box_between((cx0, cy0, DECK_Z), (cx1, cy0 + w, 2.85), WHITE, S)                           # back
    b.box_between((cx0, cy0, DECK_Z), (cx0 + w, cy1, 2.72), WHITE, S)
    b.box_between((cx1 - w, cy0, DECK_Z), (cx1, cy1, 2.72), WHITE, S)
    b.box_between((cx0, cy1 - w, DECK_Z), (cx1, cy1, 2.55), WHITE, S)
    b.box_between((cx0 + 0.03, cy0 + 0.03, 2.72), (cx1 - 0.03, cy1 - 0.03, CAB_TOP - 0.12), GLASS, S)
    b.box_between((cx0 + 0.03, cy1 - 0.1, 2.55), (cx1 - 0.03, cy1 - 0.03, 2.72), GLASS, S)
    for x in (cx0 + 0.03, cx1 - 0.03):
        for y in (cy0 + 0.03, cy1 - 0.03):
            b.box_between((x - 0.035, y - 0.035, 2.55), (x + 0.035, y + 0.035, CAB_TOP - 0.1), WHITE, S)
    # door on the left: its frame and handle
    door = rv.Wall(b, (cx0 - 0.002, 0, 0), (0, -1, 0), (0, 0, 1), S)
    door.seams(-cy1 + 0.25, DECK_Z + 0.05, -cy1 + 0.95, CAB_TOP - 0.15, WHITE)
    door.plate(-cy1 + 0.85, 2.95, -cy1 + 0.9, 3.08, 0.03, DARK)
    # roof with a sun visor over the front, a beacon, work lights front and back
    b.box_between((cx0 - 0.08, cy0 - 0.08, CAB_TOP - 0.12), (cx1 + 0.08, cy1 + 0.25, CAB_TOP), WHITE, S)
    b.box_between((cx0 + 0.1, cy0 + 0.1, CAB_TOP), (cx1 - 0.1, cy1 - 0.1, CAB_TOP + 0.08), WHITE, S)
    b.cylinder(0.07, 0.13, (cx0 + 0.35, cy0 + 0.35, CAB_TOP + 0.145), BEACON, S, segments=12)
    front = rv.Wall(b, (0, cy1 + 0.25, 0), (-1, 0, 0), (0, 0, 1), S)
    for x in (cx0 + 0.2, cx0 + 0.55, cx1 - 0.55, cx1 - 0.2):
        front.light(-x, CAB_TOP - 0.06, 0.06, LENS, DARK, depth=0.06)
    rear = rv.Wall(b, (0, cy0 - 0.08, 0), (1, 0, 0), (0, 0, 1), S)
    for x in (cx0 + 0.25, cx1 - 0.25):
        rear.light(x, CAB_TOP - 0.06, 0.05, LENS, DARK, depth=0.05)
    # wiper parked along the bottom of the windscreen
    b.rod((cx0 + 0.2, cy1 + 0.005, 2.6), (cx0 + 0.9, cy1 + 0.005, 2.66), 0.008, DARK, S)
    for x in (cx0 - 0.02, cx1 + 0.02):                                                         # mirrors
        out = 0.3 if x > 0 else -0.3
        b.rod((x, cy1 - 0.1, 3.5), (x + out, cy1 + 0.05, 3.5), 0.015, DARK, S)
        b.box_between((x + out - 0.03, cy1, 3.3), (x + out + 0.03, cy1 + 0.06, 3.6), DARK, S)
    # inside: seat, steering column and wheel, a console of levers on the right, pedals
    sx, sy, sz = CREW_POS
    b.box_between((sx - 0.25, sy - 0.25, DECK_Z), (sx + 0.25, sy + 0.2, sz), SEAT, S)
    b.box_between((sx - 0.25, sy - 0.35, sz), (sx + 0.25, sy - 0.25, sz + 0.55), SEAT, S)
    steering_wheel(b, (sx, sy + 0.42, 3.1), S)
    b.box_between((sx + 0.32, sy - 0.2, DECK_Z), (sx + 0.55, sy + 0.45, 2.75), DARK, S)
    for k in range(4):
        y = sy - 0.1 + k * 0.15
        b.rod((sx + 0.43, y, 2.75), (sx + 0.43, y + 0.03, 2.95), 0.012, DARK, S)
        b.cylinder(0.022, 0.04, (sx + 0.43, y + 0.03, 2.97), TAIL if k == 0 else RUBBER, S, segments=6)
    for x in (sx - 0.12, sx + 0.12):
        b.box_between((x - 0.05, sy + 0.55, DECK_Z), (x + 0.05, sy + 0.62, DECK_Z + 0.15), DARK, S)


def steering_wheel(b, centre, S, radius=0.2, tilt=35):
    """A rim on three spokes, its top leaning back towards the driver (tilt degrees from flat),
    on a short column into a pedestal standing on the floor"""
    c = Vector(centre)
    m = Matrix.Rotation(math.radians(tilt), 3, "X")         # the wheel's axis: up and back (-y)
    axis = m @ Vector((0, 0, 1))
    n = 16
    rim = [c + m @ Vector((radius * math.cos(2 * math.pi * k / n), radius * math.sin(2 * math.pi * k / n), 0))
           for k in range(n)]
    for k in range(n):
        b.rod(rim[k], rim[(k + 1) % n], 0.016, RUBBER, S, segments=6)
    for k in range(3):
        a = 2 * math.pi * (k / 3 + 0.25)
        b.rod(c, c + m @ Vector(((radius - 0.01) * math.cos(a), (radius - 0.01) * math.sin(a), 0)), 0.01, DARK, S,
              segments=5)
    b.rod(c - axis * 0.03, c + axis * 0.02, 0.035, DARK, S, segments=10)                  # hub
    foot = c - axis * 0.33
    b.rod(foot, c - axis * 0.03, 0.03, DARK, S)
    b.box_between((foot.x - 0.06, foot.y - 0.06, DECK_Z), (foot.x + 0.06, foot.y + 0.08, foot.z + 0.04), DARK, S)


def feeder(b):
    """The feeder house: its sides, ribs along them, the chain drive guard on the left"""
    G = "feeder"
    b.prism_x(feeder_quad(), -FEEDER_HALF_W, FEEDER_HALF_W, GREEN, G)
    (py, pz), (fy, fz) = FEEDER_PIVOT, FEEDER_FRONT
    for side in (-1, 1):
        x = side * (FEEDER_HALF_W + 0.02)
        for f in (0.3, 0.6):
            b.rod((x, py - 0.15 + (fy - py + 0.15) * f, pz + 0.3 + (fz - pz - 0.3) * f + 0.02),
                  (x, py - 0.15 + (fy - py + 0.15) * f, pz - 0.3 + (fz - pz) * f - 0.05), 0.02, GREEN, G)
    b.prism_x([(py - 0.1, pz + 0.2), (py - 0.1, pz - 0.2), (fy - 0.1, fz - 0.15), (fy - 0.1, fz + 0.2)],
              -FEEDER_HALF_W - 0.12, -FEEDER_HALF_W - 0.02, DARK, G)
    b.cylinder(0.12, 0.08, (-FEEDER_HALF_W - 0.07, py - 0.05, pz), DARK, G, segments=12, rot=X_AXIS_ROT)


def build_visual(mats):
    b = MeshBuilder()
    S = ()
    body(b, S)
    tank_and_hood(b, S)
    deck_and_cab(b, S)
    feeder(b)
    header_parts(b, GREEN, DARK, "header")
    reel(b, WHITE, DARK, "reel")
    header_auger(b, GREEN, DARK, "header_auger")
    unloading_auger(b, GREEN, DARK, "auger")
    return b.to_object("Combine_LOD1", mats)


def collision_parts(kind):
    """Convex parts of a collision LOD. kind: geometry, or fire (fire and view geometry: damage
    zone selections and the get-in target)."""
    dmg = kind == "fire"

    def parts(b, comp):
        def zone(name):
            return [name] if dmg else []

        b.box_between((-BODY_X, -1.7, BODY_Z[0]), (BODY_X, BODY_Y[1], BODY_Z[1]), 0,
                      comp("m_body", *zone("dmgZone_chassis")))
        b.box_between((-REAR_X, BODY_Y[0], 1.05), (REAR_X, -1.7, BODY_Z[1]), 0, comp("m_rear", *zone("dmgZone_chassis")))
        x0, y0, x1, y1, z0, z1 = TANK
        b.box_between((x0, y0, z0), (x1, y1, z1), 0, comp("m_tank", *zone("dmgZone_fueltank")))
        hx0, hy0, hx1, hy1, hz0, hz1 = HOOD
        b.box_between((hx0, hy0, hz0), (hx1, hy1, hz1), 0, comp("m_hood", *zone("dmgZone_engine")))
        dx0, dy0, dx1, dy1 = DECK
        b.box_between((dx0, dy0, DECK_Z - 0.06), (dx1, dy1, DECK_Z), 0, comp("m_deck", *zone("dmgZone_chassis")))
        cx0, cy0, cx1, cy1 = CAB
        b.box_between((cx0, cy0, DECK_Z), (cx1, cy1, CAB_TOP), 0, comp("m_cab", *zone("dmgZone_chassis")))
        if dmg:
            # Getting in: aim at the ladder and the cab's left side from the ground, like a door
            b.box_between((dx0 - 0.35, 1.6, 0.4), (cx0 + 0.3, 2.3, CAB_TOP), 0, comp("seat_driver"))
        # The physics (geometry) keeps the feeder and header well up off the ground, the header's
        # front a ramp, so they ride over the ground's bumps instead of catching on them (DayZ's
        # wheels are only ground probes); fire and view geometry follow the visual
        feeder = feeder_quad()
        hy0b, hy1b = HEADER_Y
        if kind == "geometry":
            feeder[2] = (feeder[2][0], feeder[2][1] + HEADER_LIFT)
            z = HEADER_Z + HEADER_LIFT
            header = [(hy0b - 0.06, z), (hy1b - 0.4, z), (hy1b + 0.14, z + 0.25), (hy1b - 0.35, HEADER_Z + 0.75),
                      (hy0b + 0.45, 1.15), (hy0b - 0.06, 1.15)]
        else:
            header = [(hy0b - 0.06, HEADER_Z), (hy1b + 0.14, HEADER_Z), (hy1b - 0.35, HEADER_Z + 0.5),
                      (hy0b + 0.45, 1.15), (hy0b - 0.06, 1.15)]
        b.prism_x(feeder, -FEEDER_HALF_W, FEEDER_HALF_W, 0, comp("m_feeder", "feeder", *zone("dmgZone_header")))
        b.prism_x(header, -HEADER_HALF_W, HEADER_HALF_W, 0, comp("m_header", "header", *zone("dmgZone_header")))
        if kind == "geometry":
            WHEELS.hubs(b, comp)

    return parts


def memory_points():
    pts = {}
    WHEELS.memory_points(pts)
    py, pz = FEEDER_PIVOT
    pts["feeder_axis"] = [(-0.6, py, pz), (0.6, py, pz)]
    pts["reel_axis"] = [(-0.6, *REEL_C), (0.6, *REEL_C)]
    pts["header_auger_axis"] = [(-0.6, *AUGER_C), (0.6, *AUGER_C)]
    fx, fy, fz = AUGER_FOOT
    pts["auger_axis"] = [(fx, fy, fz), (fx, fy, fz + 1.0)]
    # The front of the header: what the running header catches (BM_Combine.c)
    hy1 = HEADER_Y[1]
    pts["header_catch_l"] = (-HEADER_HALF_W, hy1, HEADER_Z + 0.5)
    pts["header_catch_r"] = (HEADER_HALF_W, hy1, HEADER_Z + 0.5)
    # Getting in from the left, at the foot of the ladder
    pts["pos_driver"] = (-2.0, 1.95, 0.0)
    pts["pos_driver_dir"] = (-1.5, 1.95, 0.0)
    pts["seat_con_1_1"] = (-1.85, 1.95, 0.3)
    pts["crewDriver"] = CREW_POS
    pts["ptcexhaust_start"] = (0.75, -2.0, 3.65)
    pts["ptcexhaust_end"] = (0.75, -2.0, 3.85)
    pts["ptcenginepos"] = (0.0, -2.8, 2.9)
    pts["ptccoolantpos"] = (0.0, -3.6, 2.8)
    pts["pos_carhorn"] = (0.0, 2.0, 2.5)
    pts["dmgZone_engine"] = (0.0, -2.8, 2.9)
    pts["dmgZone_fueltank"] = (0.0, -0.2, 3.0)
    pts["dmgZone_header"] = (0.0, 3.8, 0.6)
    pts["ce_center"] = (0.0, 0.0, 2.0)
    pts["ce_radius"] = (0.0, 0.0, 7.0)
    return pts


def report_model_cfg():
    for name, (a0, a1, speed) in JOINTS.items():
        print(f"[combine] {name}: angle0 rad {a0} angle1 rad {a1}, initPhase {-a0 / (a1 - a0):.4f}, "
              f"animPeriod {1 / speed:.1f}")
    WHEELS.report("combine")


def main():
    rv.enable_addon()
    front, rear = WHEELS.axles
    for axle, name, rim_r, lugs, depth in ((front, "front", 0.48, 22, 0.035), (rear, "rear", 0.26, 16, 0.02)):
        wheeled.build_wheel(os.path.join(MODEL_DIR, "proxy", f"bm_combine_wheel_{name}.p3d"), axle.radius, axle.width,
                            rim_r=rim_r, lugs=lugs, lug_depth=depth, rim_mat_name="paint_cream", rim_color=CREAM,
                            rim_weathered=True)

    rv.reset_scene()
    visual = build_visual(materials())
    geometry = crawler.collision_object("Combine_Geometry", collision_parts("geometry"), MASSES)
    fire = crawler.collision_object("Combine_Fire", collision_parts("fire"))
    view = crawler.collision_object("Combine_View", collision_parts("fire"))
    print(f"[combine] mass {sum(MASSES.values())} kg")
    report_model_cfg()
    crawler.assemble("combine", visual, geometry, fire, view, memory_points(), WHEELS, CREW_POS, BATTERY_POS,
                     os.path.join(MODEL_DIR, "bm_combine.p3d"), preview=((0, 0.5, 1.6), (9.5, 10.5, 5.5)))


main()
