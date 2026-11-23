"""Procedurally builds the drivable crawler bulldozer for the BigMachines mod.

Run headless from the project root:
    blender --background --python blender/build_bulldozer.py

Outputs:
    BigMachines/bulldozer/bm_bulldozer.p3d          the machine (MLOD; tools/build.sh binarizes it)
    BigMachines/bulldozer/proxy/bm_dozer_roller.p3d the sprocket/idler shown at each physics wheel
    models/bulldozer.blend, models/bulldozer_preview.png

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

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv  # noqa: E402
from rv import MeshBuilder, X_AXIS_ROT  # noqa: E402
from mathutils import Matrix  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "models")
MODEL_DIR = os.path.join(ROOT, "BigMachines", "bulldozer")
ROLLER_PATH = "BigMachines\\bulldozer\\proxy\\bm_dozer_roller.p3d"
CREW_PROXY = "dz\\vehicles\\wheeled\\proxies\\crew_driver.p3d"
CREW_POS = (0.0, -0.85, 1.62)
CREW_ROT = (0, 0, 180)            # the proxy faces its -Y: without this the driver sat facing backwards
BATTERY_PROXY = "dz\\vehicles\\parts\\battery_truck.p3d"     # driver's seat proxy, on the cushion

# --- Tracks and physics wheels ---
TRACK_X = 1.05          # track centre line, either side
TRACK_W = 0.56          # track shoe width
TRACK_T = 0.07          # track thickness
WHEELBASE = 2.66        # idler centre to sprocket centre
TRACK_R = 0.42          # idler/sprocket radius (the track's inner radius at the ends)
WHEEL_Z = TRACK_R + TRACK_T   # hub height: the track's bottom is on the ground
WHEEL_R = WHEEL_Z       # physics wheel radius (config BM_DozerRoller radius)
ROLLER_VIS_R = 0.40     # drawn sprocket/idler radius, inside the track

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

YELLOW, DARK, RUBBER, SEAT, CHROME = 0, 1, 2, 3, 4


def materials():
    return [
        rv.color_material("paint_yellow", (0.80, 0.55, 0.08), 0.55, 0.3),
        rv.color_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7),
        rv.color_material("track_steel", (0.10, 0.09, 0.08), 0.8, 0.6),
        rv.color_material("seat_vinyl", (0.06, 0.06, 0.06), 0.7, 0.0),
        rv.color_material("cylinder_chrome", (0.70, 0.70, 0.72), 0.25, 1.0),
    ]


def moldboard_profile(r_front, thickness, centre=(3.05, 0.68), steps=10):
    """Closed (y, z) profile of the curved blade plate: the front face is concave, bottom
    and top edges forward. Rest pose: bottom edge 0.10 above the ground."""
    cy, cz = centre
    front, back = [], []
    for i in range(steps + 1):
        a = math.radians(230 - 100 * i / steps)      # bottom edge -> top edge
        front.append((cy + r_front * math.cos(a), cz + r_front * math.sin(a)))
        back.append((cy + (r_front + thickness) * math.cos(a), cz + (r_front + thickness) * math.sin(a)))
    return front + list(reversed(back))


def build_visual(mats):
    b = MeshBuilder()

    # Tracks: belt round the idler and sprocket, frame inside, small rollers on the bottom run
    for side in (-1, 1):
        x0, x1 = side * TRACK_X - TRACK_W / 2, side * TRACK_X + TRACK_W / 2
        b.band_x(rv.stadium(WHEELBASE, TRACK_R, WHEEL_Z, segments=12), TRACK_T, x0, x1, RUBBER)
        b.box_between((side * TRACK_X - 0.2, -1.25, 0.22), (side * TRACK_X + 0.2, 1.25, 0.72), DARK)
        for y in (-0.8, -0.27, 0.27, 0.8):
            b.cylinder(0.14, 0.42, (side * TRACK_X, y, TRACK_T + 0.14), DARK, segments=12, rot=X_AXIS_ROT)
        b.cylinder(0.09, 0.3, (side * TRACK_X, 0, 2 * WHEEL_Z - TRACK_T - 0.09), DARK, segments=10, rot=X_AXIS_ROT)

    # Main frame/hull between the tracks, and fenders over them
    b.box_between((-0.78, -1.75, 0.55), (0.78, 1.55, 1.2), YELLOW)
    for side in (-1, 1):
        x0, x1 = sorted((side * 0.78, side * 1.36))
        b.box_between((x0, -1.75, 1.0), (x1, 1.15, 1.06), YELLOW)

    # Engine hood with a sloped front edge, radiator grille, guard, exhaust and air intake
    hood = [(0.05, 1.2), (1.55, 1.2), (1.55, 1.82), (1.42, 1.95), (0.05, 1.95)]
    b.prism_x(hood, -0.62, 0.62, YELLOW)
    b.box_between((-0.5, 1.55, 1.27), (0.5, 1.59, 1.78), DARK)
    b.box_between((-0.70, 1.55, 0.55), (0.70, 1.92, 1.15), DARK)
    b.cylinder(0.06, 0.75, (0.38, 1.2, 2.3), DARK, segments=10)
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
        b.prism_x(moldboard_profile(0.80, 0.14), x - 0.05, x + 0.05, YELLOW, "blade")
    for side in (-1, 1):                                                                 # end bits
        x0, x1 = sorted((side * (BLADE_HALF_W - 0.02), side * (BLADE_HALF_W + 0.03)))
        b.box_between((x0, 2.3, 0.08), (x1, 2.62, 1.2), DARK, "blade")

    # Lift cylinders: barrel swings about its hood mount ("blade_cyl"), rod rides the blade
    for side in (-1, 1):
        x = side * CYL_X
        top = (x, *CYL_TOP)
        bot = (x, *CYL_BLADE)
        d = (bot[1] - top[1], bot[2] - top[2])
        length = math.hypot(*d)
        u = (d[0] / length, d[1] / length)
        b.rod(top, (x, top[1] + u[0] * 0.62, top[2] + u[1] * 0.62), 0.075, DARK, "blade_cyl", segments=10)
        b.rod((x, bot[1] - u[0] * 0.75, bot[2] - u[1] * 0.75), bot, 0.04, CHROME, "blade", segments=8)

    obj = b.to_object("Bulldozer_LOD1", mats)
    return obj


def collision_parts(b, kind):
    """Convex boxes shared by the collision LODs. kind: geometry, or fire (fire and view
    geometry: damage zone selections and the seat)."""
    dmg = kind == "fire"

    def comp(*extra):
        return b.component(*extra)

    b.box_between((-0.78, -1.75, 0.55), (0.78, 1.55, 1.2), 0, comp("m_hull", *(["dmgZone_chassis"] if dmg else [])))
    b.box_between((-0.62, 0.05, 1.2), (0.62, 1.55, 1.95), 0, comp("m_hood", *(["dmgZone_engine"] if dmg else [])))
    b.box_between((-0.70, 1.55, 0.55), (0.70, 1.92, 1.15), 0, comp("m_nose", *(["dmgZone_chassis"] if dmg else [])))
    b.box_between((-0.75, -1.75, 1.2), (0.75, -1.25, 1.75), 0, comp("m_tank", *(["dmgZone_fueltank"] if dmg else [])))
    for side, name in ((-1, "m_track_l"), (1, "m_track_r")):
        x0, x1 = sorted((side * (TRACK_X - TRACK_W / 2), side * (TRACK_X + TRACK_W / 2)))
        # Geometry stays clear of the ground: the wheels carry the machine
        b.box_between((x0, -1.6, 0.25), (x1, 1.6, 1.0), 0, comp(name, *(["dmgZone_chassis"] if dmg else [])))
    b.box_between((-0.82, -1.75, 2.95), (0.82, 0.1, 3.05), 0, comp("m_roof", *(["dmgZone_chassis"] if dmg else [])))
    for x in (-0.72, 0.72):
        for y in (-1.62, -0.05):
            b.box_between((x - 0.05, y - 0.05, 1.2), (x + 0.05, y + 0.05, 2.95), 0,
                          comp("m_posts", *(["dmgZone_chassis"] if dmg else [])))
    for side in (-1, 1):
        x0, x1 = sorted((side * ARM_X[0], side * ARM_X[1]))
        b.box_between((x0, -0.05, 0.4), (x1, 2.3, 0.6), 0, comp("m_arms", "blade", *(["dmgZone_blade"] if dmg else [])))
    b.box_between((-BLADE_HALF_W, 2.25, 0.10), (BLADE_HALF_W, 2.64, 1.26), 0,
                  comp("m_blade", "blade", *(["dmgZone_blade"] if dmg else [])))
    if kind == "geometry":
        # The car simulation finds each wheel hub as a component of this name in the
        # Geometry LOD (vanilla does the same): a small block at the hub, inside the track
        for side_i, x in ((1, -TRACK_X), (2, TRACK_X)):
            for axle_i, y in ((1, WHEELBASE / 2), (2, -WHEELBASE / 2)):
                b.box((0.04, 0.04, 0.04), (x, y, WHEEL_Z), 0, comp(f"wheel_{side_i}_{axle_i}_damper_land", "m_hubs"))
    if dmg:
        # The seat: the get-in action's target (Crew Driver actionSel = "seat_driver")
        b.box_between((-0.35, -1.2, 1.2), (0.35, -0.5, 2.1), 0, comp("seat_driver"))


def build_collision(name, kind):
    b = MeshBuilder()
    collision_parts(b, kind)
    obj = b.to_object(name, [], triangulate_all=True)
    if kind == "geometry":
        rv.set_component_masses(obj, MASSES)
    # Mass groups only steer set_component_masses; drop them from the export
    for g in list(obj.vertex_groups):
        if g.name.startswith("m_"):
            obj.vertex_groups.remove(g)
    return obj


def memory_points():
    pts = {}
    for side_i, x in ((1, -TRACK_X), (2, TRACK_X)):
        for axle_i, y in ((1, WHEELBASE / 2), (2, -WHEELBASE / 2)):
            w = f"wheel_{side_i}_{axle_i}"
            pts[w] = (x, y, WHEEL_Z)
            pts[w + "_axis"] = [(x - 0.2, y, WHEEL_Z), (x + 0.2, y, WHEEL_Z)]
            pts[w + "_damper_land"] = (x, y, WHEEL_Z)
    pts["blade_axis"] = [(-1.5, BLADE_PIVOT[0], BLADE_PIVOT[1]), (1.5, BLADE_PIVOT[0], BLADE_PIVOT[1])]
    pts["blade_cyl_axis"] = [(-CYL_X, *CYL_TOP), (CYL_X, *CYL_TOP)]
    # Getting in from the left, beside the track (seat_con_1_1: stand within 1 m of it)
    pts["pos_driver"] = (-1.85, -0.75, 0.0)
    pts["pos_driver_dir"] = (-1.35, -0.75, 0.0)
    pts["seat_con_1_1"] = (-1.75, -0.75, 0.3)
    pts["crewDriver"] = (0.0, -0.85, 1.62)
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


def add_attachment_proxies(lod_obj, coll):
    """Proxies for the attachment slots, each in its slot's selection: the four rollers
    (wheel_<side>_<axle>) and the truck battery."""
    for side_i, x in ((1, -TRACK_X), (2, TRACK_X)):
        for axle_i, y in ((1, WHEELBASE / 2), (2, -WHEELBASE / 2)):
            rv.add_proxy(lod_obj, coll, ROLLER_PATH, (x, y, WHEEL_Z), index=2 * (side_i - 1) + axle_i,
                         groups=(f"wheel_{side_i}_{axle_i}",))
    rv.add_proxy(lod_obj, coll, BATTERY_PROXY, (0.52, -0.4, 1.2), groups=("battery",))


def cylinder_angles():
    """Lift cylinder barrel angles (degrees, about its hood mount) at blade phase 0 and 1,
    relative to the modelled pose, for model.cfg."""
    py, pz = BLADE_PIVOT
    by, bz = CYL_BLADE[0] - py, CYL_BLADE[1] - pz

    def mount_dir(blade_deg):
        a = math.radians(blade_deg)
        y = py + by * math.cos(a) - bz * math.sin(a)
        z = pz + by * math.sin(a) + bz * math.cos(a)
        return math.degrees(math.atan2(z - CYL_TOP[1], y - CYL_TOP[0]))

    rest = mount_dir(0)
    return mount_dir(BLADE_MIN_DEG) - rest, mount_dir(BLADE_MAX_DEG) - rest


def build_roller():
    """The sprocket/idler wheel model drawn at each physics wheel (the wheel item)."""
    rv.reset_scene()
    dark = rv.color_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7)
    b = MeshBuilder()
    w = 0.30
    b.lathe_x([(-w / 2, 0.10), (-w / 2, ROLLER_VIS_R), (w / 2, ROLLER_VIS_R), (w / 2, 0.10)], (0, 0, 0), 0,
              segments=16)
    b.cylinder(0.12, w + 0.1, (0, 0, 0), 0, segments=12, rot=X_AXIS_ROT)
    for k in range(8):   # sprocket teeth
        a = 2 * math.pi * k / 8
        b.box((w * 0.8, 0.12, 0.08), (0, (ROLLER_VIS_R + 0.03) * math.cos(a), (ROLLER_VIS_R + 0.03) * math.sin(a)), 0,
              rot=Matrix.Rotation(a, 4, "X"))
    vis = b.to_object("Roller_LOD1", [dark])
    rv.set_lod(vis, rv.LOD_VISUAL, resolution=1)
    rv.new_collection("Roller_Visual").objects.link(vis)

    g = MeshBuilder()
    g.box((w, 2 * WHEEL_R, 2 * WHEEL_R), (0, 0, 0), 0, g.component())   # wheel radius comes from this
    geo = g.to_object("Roller_Geometry", [], triangulate_all=True)
    rv.set_component_masses(geo, {"Component01": 150})
    rv.set_lod(geo, rv.LOD_GEOMETRY, properties=(("autocenter", "0"),))
    rv.new_collection("Roller_Geometry").objects.link(geo)
    os.makedirs(os.path.join(MODEL_DIR, "proxy"), exist_ok=True)
    rv.turn_around()
    rv.export_p3d(os.path.join(MODEL_DIR, "proxy", "bm_dozer_roller.p3d"))


def main():
    rv.enable_addon()
    build_roller()

    rv.reset_scene()
    os.makedirs(OUT_DIR, exist_ok=True)
    mats = materials()

    lod1 = rv.new_collection("LOD1_Visual")
    visual = build_visual(mats)
    lod1.objects.link(visual)
    rv.set_lod(visual, rv.LOD_VISUAL, resolution=1)
    add_attachment_proxies(visual, lod1)
    rv.add_proxy(visual, lod1, CREW_PROXY, CREW_POS, CREW_ROT, groups=("crewDriver",))

    geo_c = rv.new_collection("Geometry")
    geometry = build_collision("Bulldozer_Geometry", "geometry")
    geo_c.objects.link(geometry)
    rv.set_lod(geometry, rv.LOD_GEOMETRY, properties=(("autocenter", "0"), ("class", "vehicle")))
    # No Geometry PhysX LOD: vanilla vehicles have none, and with one the car simulation
    # fits no wheels
    fire_c = rv.new_collection("FireGeometry")
    fire = build_collision("Bulldozer_Fire", "fire")
    fire_c.objects.link(fire)
    rv.set_lod(fire, rv.LOD_FIRE_GEOMETRY)
    view_c = rv.new_collection("ViewGeometry")
    view = build_collision("Bulldozer_View", "fire")
    view_c.objects.link(view)
    rv.set_lod(view, rv.LOD_VIEW_GEOMETRY)
    # The engine looks the driver's seat proxy up in the view geometry too (without it the
    # physics setup fails: no wheels); fire geometry carries it like vanilla's
    # The car simulation fits a wheel only where the slot's proxy is in the fire geometry
    # (BI wiki: DayZ Vehicle Configuration); vanilla has them in the view geometry as well
    for lod_obj, coll in ((view, view_c), (fire, fire_c)):
        rv.add_proxy(lod_obj, coll, CREW_PROXY, CREW_POS, CREW_ROT, groups=("crewDriver",))
        add_attachment_proxies(lod_obj, coll)

    mem_c = rv.new_collection("Memory")
    memory = rv.memory_object("Bulldozer_Memory", memory_points())
    mem_c.objects.link(memory)
    rv.set_lod(memory, rv.LOD_MEMORY)

    for c in (geo_c, fire_c, view_c):
        for o in c.objects:
            o.display_type = "WIRE"

    tris = sum(len(p.vertices) - 2 for p in visual.data.polygons)
    lo, hi = cylinder_angles()
    print(f"[bulldozer] visual LOD: {len(visual.data.vertices)} verts, {tris} tris")
    print(f"[bulldozer] mass {sum(MASSES.values())} kg; model.cfg blade_cyl angle0 {lo:.2f} angle1 {hi:.2f}")

    rv.turn_around()
    rv.export_p3d(os.path.join(MODEL_DIR, "bm_bulldozer.p3d"))
    rv.turn_around()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "bulldozer.blend"))

    rv.render_preview(os.path.join(OUT_DIR, "bulldozer_preview.png"), (0, 0.3, 1.0), (6.5, 7.5, 4.0),
                      visual_collections=("LOD1_Visual",))


main()
