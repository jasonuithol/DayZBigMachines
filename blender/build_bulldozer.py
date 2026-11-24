"""Procedurally builds the drivable crawler bulldozer for the BigMachines mod.

Run headless from the project root:
    blender --background --python blender/build_bulldozer.py

Outputs:
    BigMachines/bulldozer/bm_bulldozer.p3d          the machine (MLOD; tools/build.sh binarizes it)
    BigMachines/bulldozer/proxy/bm_dozer_roller.p3d the sprocket/idler shown at each physics wheel
    models/bulldozer.blend, models/bulldozer_preview.png

Tracks, rollers, LOD assembly and export are shared with the other machines (crawler.py).
The machine drives on four hidden car wheels (the vanilla car simulation) placed at the
idler (front) and sprocket (rear) of each track. Their radius reaches the bottom of the
track, so the track appears to carry the machine. The wheels are attachments in slots
BM_Dozer_Roller_<side>_<axle> and are drawn by the roller proxy, which spins with them.

Coordinates: see rv.py (Blender X right, Y forward, Z up; origin on the ground, centred).
Selections the game relies on are listed next to where they're made; model.cfg in
BigMachines/ animates "blade", "blade_cyl" and the "wheel_*" selections.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawler  # noqa: E402
import rv  # noqa: E402
from mathutils import Matrix  # noqa: E402
from rv import MeshBuilder, X_AXIS_ROT  # noqa: E402

MODEL_DIR = os.path.join(crawler.ROOT, "BigMachines", "bulldozer")
TRACKS = crawler.Tracks(x=1.05, width=0.56, wheelbase=2.66, radius=0.42, thickness=0.07,
                        roller_path="BigMachines\\bulldozer\\proxy\\bm_dozer_roller.p3d")
CREW_POS = (0.0, -0.85, 1.62)      # driver's seat proxy, on the cushion
BATTERY_POS = (0.52, -0.4, 1.2)

# --- Blade ---
BLADE_PIVOT = (0.0, 0.50)     # (y, z) of the push arms' pivot on the track frames
BLADE_HALF_W = 1.65
ARM_X = (1.38, 1.52)          # push arms, outside the tracks
BLADE_MIN_DEG = -1.1          # model.cfg: phase 0, cutting edge just above the ground
BLADE_MAX_DEG = 15.0          # phase 1, raised about 0.7 m
CYL_TOP = (1.30, 1.90)        # (y, z) lift cylinder mount on the hood sides
CYL_BLADE = (2.25, 1.05)      # (y, z) lift cylinder mount on the blade back
CYL_X = 0.74

# --- Masses (kg) per geometry component group ---
MASSES = {
    "m_hull": 5200, "m_hood": 1500, "m_nose": 500, "m_tank": 600,
    "m_track_l": 1500, "m_track_r": 1500, "m_roof": 250, "m_posts": 80,
    "m_arms": 400, "m_blade": 1800, "m_hubs": 200,
}

YELLOW, DARK, RUBBER, SEAT, CHROME, LENS, BEACON = range(7)
LOGO, STRIPE, LETTERS, HAZARD, BADGE = range(7, 12)     # livery decals (crawler.decal_materials)


def materials():
    return [
        rv.weathered_material("paint_yellow", (0.80, 0.55, 0.08), 0.55, 0.3),
        rv.weathered_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7),
        rv.weathered_material("track_steel", (0.10, 0.09, 0.08), 0.8, 0.6),
        rv.color_material("seat_vinyl", (0.06, 0.06, 0.06), 0.7, 0.0),
        rv.color_material("cylinder_chrome", (0.70, 0.70, 0.72), 0.25, 1.0),
        *crawler.detail_materials(),
        *crawler.decal_materials("bm_badge_dozer_ca"),
    ]


def moldboard_profile(r_front, thickness, centre=(3.05, 0.68), steps=10, arc=(230, 130)):
    """Closed (y, z) profile of the curved blade plate: the front face is concave, bottom
    and top edges forward. Rest pose: bottom edge 0.10 above the ground. `arc` is the
    angle range (degrees round `centre`), bottom edge first."""
    cy, cz = centre
    front, back = [], []
    for i in range(steps + 1):
        a = math.radians(arc[0] + (arc[1] - arc[0]) * i / steps)      # bottom edge -> top edge
        front.append((cy + r_front * math.cos(a), cz + r_front * math.sin(a)))
        back.append((cy + (r_front + thickness) * math.cos(a), cz + (r_front + thickness) * math.sin(a)))
    return front + list(reversed(back))


def build_visual(mats):
    b = MeshBuilder()

    TRACKS.visual(b, RUBBER, DARK)

    # Main frame/hull between the tracks, and fenders over them
    b.box_between((-0.78, -1.75, 0.55), (0.78, 1.55, 1.2), YELLOW)
    for side in (-1, 1):
        x0, x1 = sorted((side * 0.78, side * 1.36))
        b.box_between((x0, -1.75, 1.0), (x1, 1.15, 1.06), YELLOW)

    # Engine hood with a sloped front edge, radiator grille, guard, exhaust and air intake
    hood = [(0.05, 1.2), (1.55, 1.2), (1.55, 1.82), (1.42, 1.95), (0.05, 1.95)]
    b.prism_x(hood, -0.62, 0.62, YELLOW)
    b.box_between((-0.70, 1.55, 0.55), (0.70, 1.92, 1.15), DARK)
    b.cylinder(0.11, 0.3, (-0.38, 1.25, 2.1), DARK, segments=12)
    for x in (-0.66, 0.66):  # lift cylinder brackets
        b.box_between((x - 0.04 if x < 0 else x, 1.2, 1.7), (x if x < 0 else x + 0.04, 1.4, 1.98), DARK)

    # Operator platform: console in front of the seat, two steering levers, seat, fuel tank
    b.box_between((-0.5, -0.1, 1.2), (0.5, 0.05, 1.68), DARK)
    for x in (-0.18, 0.18):
        b.rod((x, -0.22, 1.32), (x, -0.36, 1.86), 0.02, DARK)
        b.cylinder(0.035, 0.08, (x, -0.36, 1.88), RUBBER, segments=8)
    b.box_between((-0.27, -1.05, 1.2), (0.27, -0.6, 1.62), SEAT)
    b.box_between((-0.27, -1.13, 1.62), (0.27, -1.03, 2.25), SEAT)
    b.box_between((-0.75, -1.75, 1.2), (0.75, -1.25, 1.75), YELLOW)
    b.box_between((-0.3, -1.95, 0.6), (0.3, -1.75, 0.9), DARK)      # drawbar

    # ROPS canopy: four posts and a roof
    for x in (-0.72, 0.72):
        for y in (-1.62, -0.05):
            b.box_between((x - 0.05, y - 0.05, 1.2), (x + 0.05, y + 0.05, 2.95), YELLOW)
    b.box_between((-0.82, -1.75, 2.95), (0.82, 0.1, 3.05), YELLOW)

    # Blade assembly, lifted by the "blade" bone around the push arms' pivot
    for side in (-1, 1):
        x0, x1 = sorted((side * ARM_X[0], side * ARM_X[1]))
        b.box_between((x0, -0.05, 0.4), (x1, 2.3, 0.6), YELLOW, "blade")
        b.cylinder(0.11, 0.18, (side * sum(ARM_X) / 2, BLADE_PIVOT[0], BLADE_PIVOT[1]), DARK, "blade",
                   segments=12, rot=X_AXIS_ROT)
    b.prism_x(moldboard_profile(0.75, 0.06), -BLADE_HALF_W, BLADE_HALF_W, YELLOW, "blade")
    b.box_between((-BLADE_HALF_W, 2.5, 0.08), (BLADE_HALF_W, 2.6, 0.2), DARK, "blade")   # cutting edge
    for x in (-1.45, -0.6, 0.6, 1.45):     # back ribs, following the plate's curve behind it
        b.prism_x(moldboard_profile(0.80, 0.10, arc=(220, 140)), x - 0.05, x + 0.05, YELLOW, "blade")
    for side in (-1, 1):                                                                 # end bits
        x0, x1 = sorted((side * (BLADE_HALF_W - 0.02), side * (BLADE_HALF_W + 0.03)))
        b.box_between((x0, 2.3, 0.08), (x1, 2.62, 1.2), DARK, "blade")

    # Lift cylinders: barrel swings about its hood mount ("blade_cyl"), rod rides the blade
    for side in (-1, 1):
        crawler.cylinder(b, side * CYL_X, CYL_TOP, CYL_BLADE, 0.62, 0.75, DARK, CHROME, "blade_cyl", "blade_rod")

    details(b)
    obj = b.to_object("Bulldozer_LOD1", mats)
    return obj


HOOD_X = 0.62
HOOD_TOP = 1.95


def details(b):
    """Radiator grille, hood hatch and grille, side doors, exhaust, canopy lights, livery"""
    # Front: the radiator behind a louvred grille
    front = rv.Wall(b, (0, 1.55, 0), (-1, 0, 0), (0, 0, 1))
    front.grille(-0.5, 1.27, 0.5, 1.78, DARK, YELLOW, pitch=0.05)
    # Hood top (seen from above, front up): a hatch with a grille between the air cleaner
    # and the exhaust
    top = rv.Wall(b, (0, 0, HOOD_TOP), (1, 0, 0), (0, 1, 0))
    top.door(-0.52, 0.12, 0.52, 1.0, DARK, hinge="top")
    top.grille(-0.3, 0.3, 0.3, 0.85, DARK, YELLOW)
    b.cylinder(0.06, 0.75, (0.38, 1.2, 2.3), DARK, segments=10)                   # exhaust stack
    b.cylinder(0.085, 0.3, (0.38, 1.2, 2.2), DARK, segments=10)                   # heat guard
    b.cylinder(0.075, 0.012, (0.38, 1.22, 2.68), DARK, segments=10,
               rot=Matrix.Rotation(math.radians(25), 4, "X"))                      # rain cap
    b.cylinder(0.12, 0.05, (-0.38, 1.25, 2.27), DARK, segments=12, radius2=0.06)   # air cleaner cap
    # Hood sides: two doors (the rear one over the air intake), a FAT band along the top,
    # the logo plate at the front
    for side in (-1, 1):
        wall = rv.Wall(b, (side * HOOD_X, 0, 0), (0, side, 0), (0, 0, 1))     # left: s runs backwards
        y = lambda v: side * v        # noqa: E731  s for a given y
        lo, hi = sorted((y(0.12), y(1.17)))
        mid = (lo + hi) / 2
        wall.door(lo, 1.27, mid - 0.03, 1.66, DARK, hinge="left")
        wall.door(mid + 0.03, 1.27, hi, 1.66, DARK, hinge="right")
        grille_s = sorted((y(0.2), y(0.6))) if side > 0 else sorted((y(0.7), y(1.1)))
        wall.grille(grille_s[0], 1.35, grille_s[1], 1.58, DARK, YELLOW)
        wall.decal(y(0.66), 1.79, 1.1, 0.14, STRIPE)
        wall.decal(y(1.37), 1.42, 0.3, 0.15, LOGO)
    # Rear of the tank: logo plate, hazard band, two lamps
    rear = rv.Wall(b, (0, -1.75, 0), (1, 0, 0), (0, 0, 1))
    rear.decal(0, 1.5, 0.5, 0.25, LOGO)
    rear.decal(0, 1.27, 1.5, 0.1, HAZARD, uv=(0, 0, 1, 0.067))
    for s in (-0.6, 0.6):
        rear.light(s, 1.6, 0.05, LENS, DARK, depth=0.05)
    # Canopy: the model number on both sides of the roof, work lights front and back, beacon
    for side in (-1, 1):
        wall = rv.Wall(b, (side * 0.82, 0, 0), (0, side, 0), (0, 0, 1))
        wall.decal(side * -0.82, 3.0, 0.4, 0.1, BADGE)
    roof_front = rv.Wall(b, (0, 0.1, 0), (-1, 0, 0), (0, 0, 1))
    roof_back = rv.Wall(b, (0, -1.75, 0), (1, 0, 0), (0, 0, 1))
    for s in (-0.55, 0.55):
        roof_front.light(s, 2.88, 0.06, LENS, DARK, depth=0.06)
        roof_back.light(s, 2.88, 0.05, LENS, DARK, depth=0.05)
    b.cylinder(0.07, 0.12, (0.55, -1.45, 3.11), BEACON, segments=12)
    # Grab handle on the left front post, where the driver climbs in
    b.rod((-0.79, -0.05, 1.45), (-0.79, -0.05, 2.35), 0.016, DARK)
    for z in (1.45, 2.35):
        b.rod((-0.77, -0.05, z), (-0.84, -0.05, z), 0.014, DARK)


def collision_parts(kind):
    """Convex boxes for a collision LOD. kind: geometry, or fire (fire and view geometry:
    damage zone selections and the seat)."""
    dmg = kind == "fire"

    def parts(b, comp):
        def zone(name):
            return [name] if dmg else []

        b.box_between((-0.78, -1.75, 0.55), (0.78, 1.55, 1.2), 0, comp("m_hull", *zone("dmgZone_chassis")))
        b.box_between((-0.62, 0.05, 1.2), (0.62, 1.55, 1.95), 0, comp("m_hood", *zone("dmgZone_engine")))
        b.box_between((-0.70, 1.55, 0.55), (0.70, 1.92, 1.15), 0, comp("m_nose", *zone("dmgZone_chassis")))
        b.box_between((-0.75, -1.75, 1.2), (0.75, -1.25, 1.75), 0, comp("m_tank", *zone("dmgZone_fueltank")))
        TRACKS.collision(b, comp, extra=zone("dmgZone_chassis"))
        b.box_between((-0.82, -1.75, 2.95), (0.82, 0.1, 3.05), 0, comp("m_roof", *zone("dmgZone_chassis")))
        for x in (-0.72, 0.72):
            for y in (-1.62, -0.05):
                b.box_between((x - 0.05, y - 0.05, 1.2), (x + 0.05, y + 0.05, 2.95), 0,
                              comp("m_posts", *zone("dmgZone_chassis")))
        for side in (-1, 1):
            x0, x1 = sorted((side * ARM_X[0], side * ARM_X[1]))
            b.box_between((x0, -0.05, 0.4), (x1, 2.3, 0.6), 0, comp("m_arms", "blade", *zone("dmgZone_blade")))
        b.box_between((-BLADE_HALF_W, 2.25, 0.10), (BLADE_HALF_W, 2.64, 1.26), 0,
                      comp("m_blade", "blade", *zone("dmgZone_blade")))
        if kind == "geometry":
            TRACKS.hubs(b, comp)
        if dmg:
            # The seat: the get-in action's target (Crew Driver actionSel = "seat_driver")
            b.box_between((-0.35, -1.2, 1.2), (0.35, -0.5, 2.1), 0, comp("seat_driver"))

    return parts


def memory_points():
    pts = {}
    TRACKS.memory_points(pts)
    pts["blade_axis"] = [(-1.5, BLADE_PIVOT[0], BLADE_PIVOT[1]), (1.5, BLADE_PIVOT[0], BLADE_PIVOT[1])]
    pts["blade_cyl_axis"] = [(-CYL_X, *CYL_TOP), (CYL_X, *CYL_TOP)]
    pts["blade_rod_axis"] = [(0, *p) for p in crawler.cylinder_rod_axis(CYL_TOP, CYL_BLADE)]
    # Getting in from the left, beside the track (seat_con_1_1: stand within 1 m of it)
    pts["pos_driver"] = (-1.85, -0.75, 0.0)
    pts["pos_driver_dir"] = (-1.35, -0.75, 0.0)
    pts["seat_con_1_1"] = (-1.75, -0.75, 0.3)
    pts["crewDriver"] = CREW_POS
    pts["ptcexhaust_start"] = (0.38, 1.2, 2.62)
    pts["ptcexhaust_end"] = (0.38, 1.2, 2.8)
    pts["ptcenginepos"] = (0.0, 1.0, 1.95)
    pts["ptccoolantpos"] = (0.0, 1.5, 1.85)
    pts["pos_carhorn"] = (0.0, 1.3, 1.6)
    pts["dmgZone_engine"] = (0.0, 0.8, 1.6)
    pts["dmgZone_fueltank"] = (0.0, -1.5, 1.5)
    pts["dmgZone_blade"] = (0.0, 2.45, 0.7)
    pts["ce_center"] = (0.0, 0.3, 1.5)
    pts["ce_radius"] = (0.0, 0.3, 4.6)
    return pts


def main():
    rv.enable_addon()
    TRACKS.build_roller(os.path.join(MODEL_DIR, "proxy", "bm_dozer_roller.p3d"))

    rv.reset_scene()
    visual = build_visual(materials())
    geometry = crawler.collision_object("Bulldozer_Geometry", collision_parts("geometry"), MASSES)
    fire = crawler.collision_object("Bulldozer_Fire", collision_parts("fire"))
    view = crawler.collision_object("Bulldozer_View", collision_parts("fire"))
    lo, hi = crawler.cylinder_swing(BLADE_PIVOT, CYL_TOP, CYL_BLADE, BLADE_MIN_DEG, BLADE_MAX_DEG)
    e0, e1 = (crawler.cylinder_extension(BLADE_PIVOT, CYL_TOP, CYL_BLADE, a) for a in (BLADE_MIN_DEG, BLADE_MAX_DEG))
    print(f"[bulldozer] mass {sum(MASSES.values())} kg; model.cfg BladeCylinders angle0 {lo:.2f} angle1 {hi:.2f}; "
          f"BladeRods offset0 {e0:.3f} offset1 {e1:.3f}")
    crawler.assemble("bulldozer", visual, geometry, fire, view, memory_points(), TRACKS, CREW_POS, BATTERY_POS,
                     os.path.join(MODEL_DIR, "bm_bulldozer.p3d"), preview=((0, 0.3, 1.0), (6.5, 7.5, 4.0)))


main()
