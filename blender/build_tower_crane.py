"""Procedurally builds the tower crane for the BigMachines mod: two models.

Run headless from the project root:
    blender --background --python blender/build_tower_crane.py

Outputs:
    BigMachines/tower_crane/bm_crane_mast.p3d         the mast: a building (it has the ladder)
    BigMachines/tower_crane/bm_tower_crane.p3d        the slewing top: a machine with a seat
    BigMachines/tower_crane/proxy/bm_crane_roller.p3d its wheels' (invisible) model
    models/crane_mast.*, models/tower_crane.*         .blend and previews

Why two: DayZ's ladders only work on buildings (HumanCommandLadder takes a Building, and the
ladder is memory points in its model), and only a vehicle has a seat that turns with it. So
the mast is a building with the ladder inside it and a walkway on top, and the top (column,
cab, jib, trolley, hook, counter-jib) is a BM_SlewingMachine standing on the walkway on four
small hidden wheels. Slewing turns the whole top, driver and all (BM_SlewingMachine).

The top's collision is only the column, the deck under the jib, the cab and the machinery
cabinet opposite it: its weight stays centred over the wheels, and the jib can swing through
anything. The jib, counter-jib and the rest are in the fire and view geometry only.

The hoist cable can't stretch, so it is eight 4 m pieces that telescope: piece k (1..8) moves
down (k - 1) / 7 of the hook's drop. Piece 1 stays at the trolley, piece 8 rides with the hook,
and with the hook up all eight lie between the trolley and the hook. Each moving piece has a
model.cfg animation, and each animation a source of its own (see BM_Machine.AddJoint).

Coordinates: see rv.py (Blender X right, Y forward = along the jib, Z up). The mast's origin
is on the ground at its centre; the top's is on the walkway at the slewing axis.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawler  # noqa: E402
import rv  # noqa: E402
import bpy  # noqa: E402
from rv import MeshBuilder, X_AXIS_ROT  # noqa: E402

MODEL_DIR = os.path.join(crawler.ROOT, "BigMachines", "tower_crane")

# --- Mast (the building) ---
MAST_HALF = 0.8             # leg centres either side of the axis (a 1.6 m square mast)
FOOT_TOP = 0.7              # top of the concrete footing
DECK_Z = 30.0               # walkway surface at the top: the top model's z = 0
MAST_BAYS = 15
DECK_HALF = 2.0             # walkway: a 4 m square
# The ladder runs up the outside of the mast's left face, climbed from the outside (-x), and
# comes up through a hatch beyond the circle the top's wheels run on (radius 0.85): a wheel over
# the hatch drops in and tips the top
LADDER_X = -1.1
LADDER_HALF_W = 0.22
# x0, x1, y0, y1: a notch in the walkway's edge, wide enough for a climber's body (a narrower
# one stops them with their head under the walkway); you step off onto the walkway beyond it
HATCH = (-2.0, -0.98, -0.5, 0.5)
STEP_OFF_X = -0.9         # just in from the notch edge: you must stand inward of it to get on at the top
RAIL_H = 1.1

# --- Top (the machine), relative to the walkway at the axis ---
COLUMN_R = 0.3              # the slewing column (clear of the ladder hatch)
PLATFORM_Z = (2.4, 2.9)     # deck under the jib root: the cab and cabinet hang off its sides
CAB = (1.0, 0.3, 2.4, 2.0)  # x0, y0, x1, y1; floor at PLATFORM_Z[0], above anyone on the walkway
CABINET = (-2.4, 0.3, -1.0, 2.0)
CREW_POS = (1.7, 1.25, 2.4 + 0.45)
# A short ladder from the walkway up to the cab's back corner: you aim at it to get in (the cab
# itself is over your head). No physics: it swings round with the top through anything.
CAB_LADDER = (1.12, 1.48, 0.24)        # x0, x1, y
JIB_Y = (1.5, 30.0)
JIB_Z = (2.9, 4.3)          # bottom chords, top chord
JIB_HALF = 0.6
COUNTER_Y = (-1.5, -12.0)
COUNTER_Z = (2.9, 3.3)
APEX = (0.0, 0.0, 9.5)
TROLLEY_Y0 = 4.0            # modelled at its innermost; travels TROLLEY_TRAVEL out
TROLLEY_TRAVEL = 24.0
TROLLEY_BOTTOM = 2.45
HOOK_GAP = 4.0              # trolley to hook block with the hook all the way up
HOOK_TOP0 = TROLLEY_BOTTOM - HOOK_GAP
HOOK_TIP0 = HOOK_TOP0 - 0.95            # the bottom of the hook, as modelled (hook up)
HOOK_TRAVEL = 27.3          # down to 0.2 m over flat ground 30 m below the walkway
CABLE_PIECES = 8
TRACKS = crawler.Tracks(x=0.6, width=0.12, wheelbase=1.2, radius=0.12, thickness=0.03,
                        roller_path="BigMachines\\tower_crane\\proxy\\bm_crane_roller.p3d")
BATTERY_POS = (-1.7, 1.0, 2.95)         # in the machinery cabinet

# Joints (BM_TowerCrane.c, config.cpp): phase 0 trolley in / hook down, phase 1 out / up
TROLLEY_SPEED = 0.1         # phase per second: 2.4 m/s
HOOK_SPEED = 0.06           # 1.6 m/s
TROLLEY_INIT = 0.25
HOOK_INIT = 1.0

MAST_MASSES = {"m_foot": 20000, "m_legs": 8000, "m_deck": 2000, "m_rails": 200, "m_ladder": 100}
# the column carries the slewing gear: heavy and low, so the top stands steady on its wheels
TOP_MASSES = {"m_column": 8000, "m_platform": 2500, "m_cab": 800, "m_cabinet": 800, "m_hubs": 100}

YELLOW, DARK, CONCRETE, SEAT, GLASS, LENS, BEACON, RED = range(8)
LOGO, STRIPE, LETTERS, HAZARD, BADGE = range(8, 13)


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
        rv.weathered_material("paint_yellow", (0.80, 0.55, 0.08), 0.55, 0.3),
        rv.weathered_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7),
        rv.weathered_material("concrete", (0.45, 0.44, 0.42), 0.95, 0.0),
        rv.color_material("seat_vinyl", (0.06, 0.06, 0.06), 0.7, 0.0),
        glass,
        *crawler.detail_materials(),
        rv.color_material("aviation_red", (0.85, 0.05, 0.03), 0.3, 0.0),
        *crawler.decal_materials("bm_badge_crane_ca"),
    ]


def rod(b, a, c, r, mat, groups=(), segments=6):
    b.rod(a, c, r, mat, groups, segments=segments)


def bar(b, a, c, w, mat, groups=()):
    """A square bar from a to c, w wide"""
    b.rod(a, c, w * 0.7, mat, groups, segments=4)


# ---------------------------------------------------------------- mast

def mast_bays():
    h = (DECK_Z - 0.15 - FOOT_TOP) / MAST_BAYS
    return [FOOT_TOP + k * h for k in range(MAST_BAYS + 1)]


def build_mast_visual(mats):
    b = MeshBuilder()
    m = MAST_HALF
    corners = [(-m, -m), (m, -m), (m, m), (-m, m)]
    # Footing with ballast blocks
    b.box_between((-2.5, -2.5, -0.4), (2.5, 2.5, FOOT_TOP), CONCRETE)
    for x, y in ((-1.7, -1.7), (1.7, -1.7), (1.7, 1.7), (-1.7, 1.7)):
        b.box_between((x - 0.6, y - 0.6, FOOT_TOP), (x + 0.6, y + 0.6, FOOT_TOP + 0.6), CONCRETE)
    # Legs, horizontals and diagonals
    levels = mast_bays()
    top = levels[-1]
    for x, y in corners:
        b.box_between((x - 0.08, y - 0.08, FOOT_TOP), (x + 0.08, y + 0.08, top), YELLOW)
        b.box_between((x - 0.15, y - 0.15, FOOT_TOP), (x + 0.15, y + 0.15, FOOT_TOP + 0.08), DARK)   # base plate
    for k, z in enumerate(levels):
        for i in range(4):
            (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
            bar(b, (x0, y0, z), (x1, y1, z), 0.06, YELLOW)
            if k == len(levels) - 1:
                continue
            z1 = levels[k + 1]
            if (k + i) % 2:
                rod(b, (x0, y0, z), (x1, y1, z1), 0.035, YELLOW)
            else:
                rod(b, (x1, y1, z), (x0, y0, z1), 0.035, YELLOW)
    # Ladder: two rails and rungs, braced to the mast, up through the hatch to above the walkway
    for y in (-LADDER_HALF_W, LADDER_HALF_W):
        b.box_between((LADDER_X - 0.02, y - 0.02, FOOT_TOP), (LADDER_X + 0.02, y + 0.02, DECK_Z + 1.0), DARK)
        for z in levels[1:-1:2]:
            bar(b, (LADDER_X, y, z), (-MAST_HALF, y, z), 0.04, DARK)
    z = FOOT_TOP + 0.3
    while z < DECK_Z + 0.9:
        rod(b, (LADDER_X, -LADDER_HALF_W, z), (LADDER_X, LADDER_HALF_W, z), 0.015, DARK, segments=6)
        z += 0.3
    # Walkway: grating with the hatch, a frame under it, handrails all round
    x0h, x1h, y0h, y1h = HATCH
    d = DECK_HALF
    for lo, hi in walkway_boxes():
        b.box_between(lo, hi, DARK)
    for i in range(4):
        (xa, ya), (xb, yb) = corners[i], corners[(i + 1) % 4]
        bar(b, (xa * d / m, ya * d / m, DECK_Z - 0.2), (xb * d / m, yb * d / m, DECK_Z - 0.2), 0.12, YELLOW)
        bar(b, (xa, ya, top), (xa * d / m, ya * d / m, DECK_Z - 0.2), 0.08, YELLOW)    # brackets
    for i in range(4):
        (xa, ya), (xb, yb) = [(c[0] * d / m, c[1] * d / m) for c in (corners[i], corners[(i + 1) % 4])]
        for h in (0.55, RAIL_H):
            rod(b, (xa, ya, DECK_Z + h), (xb, yb, DECK_Z + h), 0.025, YELLOW)
        for t in (0, 0.25, 0.5, 0.75):
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            rod(b, (px, py, DECK_Z), (px, py, DECK_Z + RAIL_H), 0.025, YELLOW)
        b.box_between((min(xa, xb) - 0.01, min(ya, yb) - 0.01, DECK_Z), (max(xa, xb) + 0.01, max(ya, yb) + 0.01,
                                                                          DECK_Z + 0.12), YELLOW)   # toe board
    # The slewing ring the top stands on
    b.cylinder(0.75, 0.15, (0, 0, DECK_Z + 0.075), DARK, segments=24)
    # FAT and a hazard band on the footing
    for wall in (rv.Wall(b, (0, -2.5, 0), (1, 0, 0), (0, 0, 1)), rv.Wall(b, (0, 2.5, 0), (-1, 0, 0), (0, 0, 1))):
        wall.decal(0, 0.15, 1.2, 0.6, LOGO)
        wall.decal(0, -0.28, 4.8, 0.16, HAZARD, uv=(0, 0, 4, 0.16))
    return b.to_object("Mast_LOD1", mats)


def walkway_boxes():
    """The walkway as boxes round the ladder hatch: (lo, hi) corners"""
    x0h, x1h, y0h, y1h = HATCH
    d = DECK_HALF
    z0, z1 = DECK_Z - 0.12, DECK_Z
    boxes = [((x1h, -d, z0), (d, d, z1)), ((x0h, y1h, z0), (x1h, d, z1)), ((x0h, -d, z0), (x1h, y0h, z1))]
    if x0h > -d:
        boxes.append(((-d, -d, z0), (x0h, d, z1)))
    return boxes


def mast_collision(kind):
    def parts(b, comp):
        b.box_between((-2.5, -2.5, -0.4), (2.5, 2.5, FOOT_TOP), 0, comp("m_foot"))
        top = mast_bays()[-1]
        for x in (-MAST_HALF, MAST_HALF):
            for y in (-MAST_HALF, MAST_HALF):
                b.box_between((x - 0.09, y - 0.09, FOOT_TOP), (x + 0.09, y + 0.09, top), 0, comp("m_legs"))
        for lo, hi in walkway_boxes():
            b.box_between(lo, hi, 0, comp("m_deck"))
        d = DECK_HALF
        for lo, hi in (((-d, -d, DECK_Z), (d, -d + 0.05, DECK_Z + RAIL_H)), ((-d, d - 0.05, DECK_Z), (d, d, DECK_Z + RAIL_H)),
                       ((-d, -d, DECK_Z), (-d + 0.05, d, DECK_Z + RAIL_H)), ((d - 0.05, -d, DECK_Z), (d, d, DECK_Z + RAIL_H))):
            b.box_between(lo, hi, 0, comp("m_rails"))
        # The ladder: the enter-ladder action looks for a component named ladder1 where the
        # crosshair is (view geometry). In the geometry it stops under the walkway: above it (the
        # rails you hold climbing off) it would block stepping off. In view geometry it goes up to
        # the rails' tops, so you can aim at it from the walkway to get on at the top.
        top_z = DECK_Z + 1.0 if kind == "view" else DECK_Z - 0.15
        b.box_between((LADDER_X - 0.04, -LADDER_HALF_W - 0.03, FOOT_TOP), (LADDER_X + 0.04, LADDER_HALF_W + 0.03,
                                                                          top_z), 0, comp("m_ladder", "ladder1"))
    return parts


def mast_memory():
    """The ladder, as in the vanilla tower crane (Land_Construction_Crane): ladder1 is the
    climbing line (first rung, top), ladder1_con the places to get on and off (top, bottom),
    ladder1_con_dir the side you stand on at each (bottom: outside the mast; top: the walkway,
    towards the mast), ladder1_dir the climbing side"""
    lx, zb, zt = LADDER_X, FOOT_TOP, DECK_Z
    sx = STEP_OFF_X         # the top's get-on/off point is on the walkway, past the hatch
    return {
        # the top end is where the climber's hands stop: 2.3 m up, their feet reach the walkway
        # and they can step off (0.5 m, as on the vanilla crane, leaves them stuck under it)
        "ladder1": [(lx, 0, zb + 0.6), (lx, 0, zt + 2.3)],
        "ladder1_dir": [(lx - 0.37, 0, zb)],
        "ladder1_con": [(sx, 0, zt), (lx, 0, zb)],
        "ladder1_con_dir": [(lx - 0.37, 0, zb), (sx + 0.4, 0, zt)],
        "ladder1_top_front": [(sx, 0, zt)],
        "ladder1_bottom_front": [(lx, 0, zb)],
    }


def build_mast():
    rv.reset_scene()
    mats = materials()
    visual = build_mast_visual(mats)
    lods = [("LOD1_Visual", visual, rv.LOD_VISUAL, (), 1)]
    geometry = crawler.collision_object("Mast_Geometry", mast_collision("geometry"), MAST_MASSES)
    fire = crawler.collision_object("Mast_Fire", mast_collision("fire"))
    view = crawler.collision_object("Mast_View", mast_collision("view"))
    lods += [("Geometry", geometry, rv.LOD_GEOMETRY, (("autocenter", "0"),), 0),
             ("FireGeometry", fire, rv.LOD_FIRE_GEOMETRY, (), 0),
             ("ViewGeometry", view, rv.LOD_VIEW_GEOMETRY, (), 0)]
    memory = rv.memory_object("Mast_Memory", mast_memory())
    lods.append(("Memory", memory, rv.LOD_MEMORY, (), 0))
    for coll_name, obj, lod, props, res in lods:
        rv.new_collection(coll_name).objects.link(obj)
        rv.set_lod(obj, lod, resolution=res, properties=props)
        if lod in (rv.LOD_GEOMETRY, rv.LOD_FIRE_GEOMETRY, rv.LOD_VIEW_GEOMETRY):
            obj.display_type = "WIRE"
    tris = sum(len(p.vertices) - 2 for p in visual.data.polygons)
    print(f"[crane_mast] visual LOD: {len(visual.data.vertices)} verts, {tris} tris")
    rv.turn_around()
    rv.export_p3d(os.path.join(MODEL_DIR, "bm_crane_mast.p3d"))
    rv.turn_around()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(crawler.OUT_DIR, "crane_mast.blend"))
    rv.render_preview(os.path.join(crawler.OUT_DIR, "crane_mast_preview.png"), (0, 0, 15), (14, -30, 18),
                      visual_collections=("LOD1_Visual",))


# ---------------------------------------------------------------- top

def jib_lattice(b, y0, y1, groups=()):
    """Triangular lattice: two bottom chords and a top chord, laced every bay"""
    zb, zt = JIB_Z
    h = JIB_HALF
    bar(b, (-h, y0, zb), (-h, y1, zb), 0.1, YELLOW, groups)
    bar(b, (h, y0, zb), (h, y1, zb), 0.1, YELLOW, groups)
    bar(b, (0, y0, zt), (0, y1, zt), 0.1, YELLOW, groups)
    n = max(1, round((y1 - y0) / 1.5))
    step = (y1 - y0) / n
    for k in range(n + 1):
        y = y0 + k * step
        rod(b, (-h, y, zb), (h, y, zb), 0.03, YELLOW, groups)
        if k < n:
            yn = y + step
            ya, yb = (y, yn) if k % 2 == 0 else (yn, y)
            rod(b, (-h, ya, zb), (0, yb, zt), 0.03, YELLOW, groups)
            rod(b, (h, ya, zb), (0, yb, zt), 0.03, YELLOW, groups)
            rod(b, (-h, y, zb), (h, yn, zb), 0.025, YELLOW, groups)
    # the nose
    rod(b, (-h, y1, zb), (0, y1, zt), 0.04, YELLOW, groups)
    rod(b, (h, y1, zb), (0, y1, zt), 0.04, YELLOW, groups)


def build_top_visual(mats):
    b = MeshBuilder()
    # Slewing column on the ring, deck under the jib root
    b.cylinder(COLUMN_R, PLATFORM_Z[0], (0, 0, PLATFORM_Z[0] / 2), YELLOW, segments=16)
    b.cylinder(0.7, 0.12, (0, 0, 0.21), DARK, segments=24)
    b.box_between((-1.0, -2.5, PLATFORM_Z[0]), (1.0, 2.0, PLATFORM_Z[1]), YELLOW)
    # Cab on the right, beside the jib root, above the walkway
    x0, y0, x1, y1 = CAB
    w = 0.04
    fz = PLATFORM_Z[0]
    b.box_between((x0, y0, fz - 0.08), (x1, y1, fz), DARK)                                  # floor
    b.box_between((x0, y0, fz), (x0 + w, y1, fz + 0.9), YELLOW)
    b.box_between((x1 - w, y0, fz), (x1, y1, fz + 0.9), YELLOW)
    b.box_between((x0 + w, y0, fz), (x1 - w, y0 + w, fz + 0.9), YELLOW)
    b.box_between((x0 + w, y1 - w, fz), (x1 - w, y1, fz + 0.5), YELLOW)                      # low front: look down
    b.box_between((x0 + 0.03, y0 + 0.03, fz + 0.9), (x1 - 0.03, y1 - 0.03, fz + 2.0), GLASS)
    b.box_between((x0 + 0.05, y1 - 0.06, fz + 0.5), (x1 - 0.05, y1 - 0.02, fz + 0.9), GLASS)
    b.box_between((x0 + 0.2, y1 + 0.02, fz - 0.6), (x1 - 0.2, y1 + 0.3, fz + 0.02), GLASS)   # floor window, forward
    for x in (x0 + 0.04, x1 - 0.04):
        for y in (y0 + 0.04, y1 - 0.04):
            b.box_between((x - 0.04, y - 0.04, fz + 0.9), (x + 0.04, y + 0.04, fz + 2.0), YELLOW)
    b.box_between((x0 - 0.02, y0 - 0.02, fz + 2.0), (x1 + 0.02, y1 + 0.02, fz + 2.1), YELLOW)
    # seat and two joysticks
    cx, cy = CREW_POS[0], CREW_POS[1]
    b.box_between((cx - 0.23, cy - 0.2, fz), (cx + 0.23, cy + 0.25, fz + 0.45), SEAT)
    b.box_between((cx - 0.23, cy - 0.3, fz + 0.45), (cx + 0.23, cy - 0.2, fz + 1.1), SEAT)
    for x in (cx - 0.33, cx + 0.33):
        b.box_between((x - 0.06, cy - 0.2, fz), (x + 0.06, cy + 0.3, fz + 0.4), DARK)
        b.rod((x, cy + 0.2, fz + 0.4), (x, cy + 0.25, fz + 0.62), 0.02, DARK)
    lx0, lx1, ly = CAB_LADDER
    for x in (lx0, lx1):
        b.box_between((x - 0.02, ly - 0.02, 0.05), (x + 0.02, ly + 0.02, fz + 0.9), DARK)
    z = 0.35
    while z < fz:
        rod(b, (lx0, ly, z), (lx1, ly, z), 0.015, DARK)
        z += 0.3
    cab_front = rv.Wall(b, (0, y1 + 0.005, 0), (-1, 0, 0), (0, 0, 1))
    cab_front.light(-(x0 + x1) / 2, fz + 2.2, 0.07, LENS, DARK)
    # Machinery cabinet on the left (balances the cab), with the battery
    x0c, y0c, x1c, y1c = CABINET
    b.box_between((x0c, y0c, fz), (x1c, y1c, fz + 1.6), YELLOW)
    left = rv.Wall(b, (x0c, 0, 0), (0, -1, 0), (0, 0, 1))
    left.door(-y1c + 0.08, fz + 0.1, -y0c - 0.08, fz + 1.5, DARK, hinge="left")
    left.grille(-y1c + 0.3, fz + 0.4, -y0c - 0.4, fz + 1.2, DARK, YELLOW)

    # Tower head: four legs to the apex, pendants to the jib and counter-jib
    for x in (-0.9, 0.9):
        for y in (-1.0, 1.0):
            bar(b, (x, y, PLATFORM_Z[1]), APEX, 0.12, YELLOW)
    rod(b, (-0.9, -1.0, 6.0), (0.9, 1.0, 6.0), 0.04, YELLOW)
    rod(b, (0.9, -1.0, 6.0), (-0.9, 1.0, 6.0), 0.04, YELLOW)
    for y in (16.0, 28.0):
        rod(b, APEX, (0, y, JIB_Z[1]), 0.03, DARK)
    for x in (-0.8, 0.8):
        rod(b, APEX, (x, COUNTER_Y[1] + 0.3, COUNTER_Z[1]), 0.03, DARK)
    b.cylinder(0.08, 0.15, (APEX[0], APEX[1], APEX[2] + 0.1), RED, segments=10)        # aviation lights
    b.cylinder(0.06, 0.12, (0, JIB_Y[1], JIB_Z[1] + 0.1), RED, segments=10)
    b.cylinder(0.06, 0.12, (0, COUNTER_Y[1], COUNTER_Z[1] + 0.1), RED, segments=10)

    # Jib
    jib_lattice(b, JIB_Y[0], JIB_Y[1])
    # FAT banner on both sides of the jib, near its root
    for side in (-1, 1):
        x = side * (JIB_HALF + 0.03)
        b.box_between((x - 0.02, 3.0, JIB_Z[0] + 0.05), (x + 0.02, 8.0, JIB_Z[1] - 0.15), YELLOW)
        banner = rv.Wall(b, (x + side * 0.02, 5.5, 0), (0, side, 0), (0, 0, 1))
        banner.decal(0, (JIB_Z[0] + JIB_Z[1]) / 2 - 0.05, 4.8, 1.0, LETTERS, uv=(0.06, 0.1, 0.94, 0.9))

    # Counter-jib: two side beams, cross members, a walkway; hoist winch; counterweights
    cy0, cy1 = COUNTER_Y
    for x in (-0.8, 0.8):
        b.box_between((x - 0.1, cy1, COUNTER_Z[0]), (x + 0.1, cy0, COUNTER_Z[1]), YELLOW)
    y = cy0
    while y > cy1:
        bar(b, (-0.8, y, COUNTER_Z[0] + 0.1), (0.8, y, COUNTER_Z[0] + 0.1), 0.08, YELLOW)
        y -= 1.5
    b.box_between((-0.7, cy1, COUNTER_Z[0] + 0.2), (0.7, cy0, COUNTER_Z[0] + 0.24), DARK)
    b.cylinder(0.35, 1.0, (0, -5.5, COUNTER_Z[0] + 0.6), DARK, segments=16, rot=X_AXIS_ROT)    # winch drum
    b.box_between((0.55, -6.0, COUNTER_Z[0] + 0.24), (0.95, -5.0, COUNTER_Z[0] + 0.9), YELLOW)  # motor
    b.box_between((-0.95, -5.9, COUNTER_Z[0] + 0.24), (-0.6, -5.1, COUNTER_Z[0] + 0.7), DARK)   # gearbox
    for k in range(4):                                   # counterweight slabs, hanging under the end
        y = cy1 + 0.25 + k * 0.62
        b.box_between((-1.1, y, 0.6), (1.1, y + 0.58, COUNTER_Z[0]), (CONCRETE))
    back = rv.Wall(b, (0, cy1 + 0.25, 0), (1, 0, 0), (0, 0, 1))
    back.decal(0, 1.75, 2.0, 1.0, LETTERS)
    for side in (-1, 1):
        wall = rv.Wall(b, (side * 1.1, 0, 0), (0, side, 0), (0, 0, 1))
        wall.decal(side * (cy1 + 1.45), 1.4, 2.0, 0.5, BADGE)
        wall.decal(side * (cy1 + 1.45), 0.75, 2.4, 0.15, HAZARD, uv=(0, 0, 2, 0.13))

    # Trolley (bone "trolley"), hook block ("hook"), cable pieces ("cable_<k>")
    ty = TROLLEY_Y0
    b.box_between((-JIB_HALF + 0.05, ty - 0.45, TROLLEY_BOTTOM), (JIB_HALF - 0.05, ty + 0.45, TROLLEY_BOTTOM + 0.35),
                  DARK, "trolley")
    for x in (-JIB_HALF, JIB_HALF):
        for y in (ty - 0.35, ty + 0.35):
            b.cylinder(0.08, 0.06, (x, y, JIB_Z[0] - 0.08), DARK, "trolley", segments=10, rot=X_AXIS_ROT)
    b.cylinder(0.18, 0.12, (0, ty, TROLLEY_BOTTOM - 0.05), DARK, "trolley", segments=12, rot=X_AXIS_ROT)
    b.box_between((-0.25, ty - 0.18, HOOK_TOP0 - 0.55), (0.25, ty + 0.18, HOOK_TOP0), YELLOW, "hook")
    b.cylinder(0.2, 0.14, (0, ty, HOOK_TOP0 - 0.15), DARK, "hook", segments=12, rot=X_AXIS_ROT)
    b.rod((0, ty, HOOK_TOP0 - 0.55), (0, ty, HOOK_TOP0 - 0.7), 0.04, DARK, "hook")
    hook_profile = []
    for i in range(10):                                  # the hook itself: a C seen from the side
        a = math.radians(90 + 290 * i / 9)
        hook_profile.append((ty + 0.13 * math.cos(a), HOOK_TIP0 + 0.13 + 0.13 * math.sin(a)))
    for (ya, za), (yb, zb) in zip(hook_profile, hook_profile[1:]):
        b.rod((0, ya, za), (0, yb, zb), 0.035, DARK, "hook", segments=6)
    b.decal((0.255, ty, HOOK_TOP0 - 0.28), (0, 1, 0), (0, 0, 1), 0.36, 0.2, HAZARD, "hook", uv=(0, 0, 1, 0.55))
    b.decal((-0.255, ty, HOOK_TOP0 - 0.28), (0, -1, 0), (0, 0, 1), 0.36, 0.2, HAZARD, "hook", uv=(0, 0, 1, 0.55))
    for k in range(1, CABLE_PIECES + 1):
        group = "trolley" if k == 1 else ("hook" if k == CABLE_PIECES else f"cable_{k}")
        for x in (-0.12, 0.12):
            b.rod((x, ty, TROLLEY_BOTTOM), (x, ty, TROLLEY_BOTTOM - HOOK_GAP), 0.012, DARK, group, segments=4)
    return b.to_object("TowerCrane_LOD1", mats)


def cable_offset(k):
    """model.cfg offset0 of cable piece k (hook all the way down); offset1 is 0"""
    return -(k - 1) * HOOK_TRAVEL / (CABLE_PIECES - 1)


def top_collision(kind):
    dmg = kind == "fire"

    def parts(b, comp):
        def zone(name):
            return [name] if dmg else []

        r = COLUMN_R - 0.02
        b.box_between((-r, -r, 0.25), (r, r, PLATFORM_Z[0]), 0, comp("m_column", *zone("dmgZone_engine")))
        b.box_between((-1.0, -2.5, PLATFORM_Z[0]), (1.0, 2.0, PLATFORM_Z[1]), 0,
                      comp("m_platform", *zone("dmgZone_chassis")))
        x0, y0, x1, y1 = CAB
        # the cab is the get-in action's target (Crew Driver actionSel = "seat_driver")
        b.box_between((x0, y0, PLATFORM_Z[0]), (x1, y1, PLATFORM_Z[0] + 2.1), 0,
                      comp("m_cab", *zone("dmgZone_chassis"), *(["seat_driver"] if dmg else [])))
        x0, y0, x1, y1 = CABINET
        b.box_between((x0, y0, PLATFORM_Z[0]), (x1, y1, PLATFORM_Z[0] + 1.6), 0,
                      comp("m_cabinet", *zone("dmgZone_fueltank")))
        if kind == "geometry":
            TRACKS.hubs(b, comp)
        else:
            lx0, lx1, ly = CAB_LADDER
            b.box_between((lx0 - 0.03, ly - 0.05, 0.05), (lx1 + 0.03, ly + 0.05, PLATFORM_Z[0]), 0,
                          comp("m_cab_ladder", *zone("dmgZone_chassis"), *(["seat_driver"] if dmg else [])))
            # shootable and in the way of sight, but no physics: the jib swings through anything
            zb, zt = JIB_Z
            b.box_between((-JIB_HALF, JIB_Y[0], zb), (JIB_HALF, JIB_Y[1], zt), 0, comp("m_jib", *zone("dmgZone_jib")))
            b.box_between((-1.1, COUNTER_Y[1], 0.6), (1.1, COUNTER_Y[0], COUNTER_Z[1]), 0,
                          comp("m_counter", *zone("dmgZone_jib")))
            b.box_between((-0.9, -1.0, PLATFORM_Z[1]), (0.9, 1.0, APEX[2]), 0, comp("m_head", *zone("dmgZone_jib")))
            # the trolley and the hook block, in their bones (the level needs some animated part
            # or the engine loses the crew and wheel proxies' bones in it)
            ty = TROLLEY_Y0
            b.box_between((-JIB_HALF + 0.05, ty - 0.45, TROLLEY_BOTTOM), (JIB_HALF - 0.05, ty + 0.45,
                                                                           TROLLEY_BOTTOM + 0.35), 0,
                          comp("m_trolley", "trolley", *zone("dmgZone_jib")))
            b.box_between((-0.25, ty - 0.2, HOOK_TIP0), (0.25, ty + 0.2, HOOK_TOP0), 0,
                          comp("m_hook", "hook", *zone("dmgZone_jib")))

    return parts


def top_memory():
    pts = {}
    TRACKS.memory_points(pts)
    pts["trolley_axis"] = [(0, TROLLEY_Y0, JIB_Z[0]), (0, TROLLEY_Y0 + 1.0, JIB_Z[0])]
    pts["hook_axis"] = [(0, TROLLEY_Y0, 0), (0, TROLLEY_Y0, 1.0)]
    pts["hook_point"] = (0, TROLLEY_Y0, HOOK_TIP0)       # the hook's tip, trolley in and hook up
    # Getting in and out on the walkway, at the cab ladder (stand within 1 m of seat_con_1_1)
    pts["pos_driver"] = (1.3, -0.35, 0.05)
    pts["pos_driver_dir"] = (1.3, -0.85, 0.05)
    pts["seat_con_1_1"] = (1.3, -0.2, 0.3)
    pts["crewDriver"] = CREW_POS
    pts["ptcexhaust_start"] = (-1.7, 1.0, 4.0)
    pts["ptcexhaust_end"] = (-1.7, 1.0, 4.1)
    pts["ptcenginepos"] = (-1.7, 1.0, 3.2)
    pts["ptccoolantpos"] = (-1.7, 1.0, 3.2)
    pts["pos_carhorn"] = (0.0, 0.0, 2.6)
    pts["dmgZone_engine"] = (0.0, 0.0, 1.2)
    pts["dmgZone_fueltank"] = (-1.7, 1.0, 3.2)
    pts["dmgZone_jib"] = (0.0, 10.0, 3.5)
    pts["ce_center"] = (0.0, 5.0, 3.0)
    pts["ce_radius"] = (0.0, 5.0, 23.0)
    return pts


def build_top():
    TRACKS.build_roller(os.path.join(MODEL_DIR, "proxy", "bm_crane_roller.p3d"))
    rv.reset_scene()
    visual = build_top_visual(materials())
    geometry = crawler.collision_object("TowerCrane_Geometry", top_collision("geometry"), TOP_MASSES)
    fire = crawler.collision_object("TowerCrane_Fire", top_collision("fire"))
    view = crawler.collision_object("TowerCrane_View", top_collision("fire"))
    print(f"[tower_crane] top mass {sum(TOP_MASSES.values())} kg")
    print(f"[tower_crane] trolley: translation offset0 0 offset1 {TROLLEY_TRAVEL}, initPhase {TROLLEY_INIT}, "
          f"animPeriod {1 / TROLLEY_SPEED:.1f}")
    print(f"[tower_crane] hook: translation offset0 {-HOOK_TRAVEL} offset1 0, initPhase {HOOK_INIT}, "
          f"animPeriod {1 / HOOK_SPEED:.1f}")
    for k in range(2, CABLE_PIECES):
        print(f"[tower_crane] cable_{k}: offset0 {cable_offset(k):.3f}")
    crawler.assemble("tower_crane", visual, geometry, fire, view, top_memory(), TRACKS, CREW_POS, BATTERY_POS,
                     os.path.join(MODEL_DIR, "bm_tower_crane.p3d"),
                     preview=((0, 6, 3), (-16, -14, 10)))


def main():
    rv.enable_addon()
    os.makedirs(os.path.join(MODEL_DIR, "proxy"), exist_ok=True)
    build_mast()
    build_top()


main()
