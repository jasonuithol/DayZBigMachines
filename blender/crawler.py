"""What every Big Machines crawler shares: tracks, the four physics rollers, the LODs a DayZ
car needs, and export. The per-machine scripts (build_bulldozer.py, build_excavator.py) model
the rest and call assemble().

A machine drives on four hidden car wheels (the vanilla car simulation) at the idler (front)
and sprocket (rear) of each track. Their radius reaches the bottom of the track, so the
track appears to carry the machine. The wheels are roller items in slots named in config.cpp,
each drawn by a proxy in the slot's selection (wheel_<side>_<axle>; side 1 = left).

What a DayZ car model needs (each of these silently broke the bulldozer until found):
- wheel hubs "wheel_X_Y_damper_land" as components in the Geometry LOD;
- the roller and battery proxies in the Fire and View Geometry LODs as well as the visual;
- the driver's proxy (selection crewDriver) in the View Geometry LOD too, and crewDriver a
  bone in model.cfg; the proxy faces its -Y, so it's turned 180 degrees;
- no Geometry PhysX LOD; Geometry LOD properties autocenter=0, class=vehicle;
- the whole model turned 180 degrees before export (rv.turn_around).
"""

import math
import os

import bpy
from mathutils import Matrix

import rv
from rv import MeshBuilder, X_AXIS_ROT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "models")
CREW_PROXY = "dz\\vehicles\\wheeled\\proxies\\crew_driver.p3d"
CREW_ROT = (0, 0, 180)     # the proxy faces its -Y: without this the driver sits facing backwards
BATTERY_PROXY = "dz\\vehicles\\parts\\battery_truck.p3d"

# The game moves the wheel bones (wheel_<side>_<axle>) with the suspension itself, whatever
# model.cfg says: wheel items were drawn 15-28 cm above their hubs and anything in those bones
# jumps about, even parked with the engine off. So the rollers' own model is invisible and the
# sprockets and idlers are drawn by the machine, in the tread bones (they turn with the treads).
# Their teeth stop this far inside the belt. (Gear bones animated off the wheel sources once
# silently stopped every animation in the model: never let two animations share a source.)
GEAR_CLEARANCE = 0.02

# Track shoes (Tracks.treads): about this pitch (m), within these limits, a gap between shoes,
# the plate's thickness and the grouser bar's height and length along the track. The plate
# is on the belt's inside; the grouser stands 5 mm proud of it (into the ground).
TREAD_PITCH, TREAD_PITCH_MIN, TREAD_PITCH_MAX = 0.19, 0.16, 0.23
TREAD_GAP = 0.012
TREAD_PLATE = 0.04
TREAD_GROUSER = 0.035
TREAD_GROUSER_LEN = 0.045

# Livery decals (tools/make_textures.py draws them; tools/img2paa.sh makes the .paa)
DECALS = ("bm_fat_logo_ca", "bm_fat_stripe_ca", "bm_fat_letters_ca", "bm_hazard_ca")


def decal_materials(badge):
    """Texture materials for the livery, in DECALS order, then `badge` (a model number)"""
    mats = []
    for name in (*DECALS, badge):
        mats.append(rv.texture_material(name, f"BigMachines\\data\\{name}.paa",
                                        os.path.join(ROOT, "textures", name + ".png")))
    return mats


def detail_materials():
    """Light lenses and a beacon"""
    return [
        rv.color_material("lens", (0.95, 0.92, 0.78), 0.1, 0.0),
        rv.color_material("beacon", (0.95, 0.45, 0.03), 0.2, 0.0),
    ]


class Tracks:
    """A crawler undercarriage: two tracks round an idler and a sprocket."""

    def __init__(self, x, width, wheelbase, radius, thickness, roller_path):
        self.x = x                      # track centre line, either side
        self.width = width              # track shoe width
        self.wheelbase = wheelbase      # idler centre to sprocket centre
        self.radius = radius            # idler/sprocket radius (the track's inner radius at the ends)
        self.thickness = thickness
        self.wheel_z = radius + thickness   # hub height: the track's bottom is on the ground
        self.wheel_r = self.wheel_z         # physics wheel radius (the roller item's config radius)
        self.roller_path = roller_path      # in-game path of the roller (wheel item) model
        self.tooth_r = radius - GEAR_CLEARANCE      # sprocket tooth tips, inside the belt

    def wheels(self):
        """(slot selection, x, y) of the four physics wheels"""
        for side_i, x in ((1, -self.x), (2, self.x)):
            for axle_i, y in ((1, self.wheelbase / 2), (2, -self.wheelbase / 2)):
                yield f"wheel_{side_i}_{axle_i}", x, y

    def tread_layout(self):
        """How the shoes go round: (n, straight pitch, m, curve pitch, curve step in radians).
        n shoes on each straight run and m round each end, pitches as near equal as the track
        allows (each shoe moves one pitch per animation cycle, model.cfg Tread*)."""
        rc = self.radius + self.thickness / 2       # the shoes' pitch line round the ends
        best = None
        for n in range(4, 40):
            for m in range(3, 20):
                ps, pc = self.wheelbase / n, math.pi * rc / m
                if not TREAD_PITCH_MIN <= ps <= TREAD_PITCH_MAX:
                    continue
                score = abs(ps - pc) / pc + abs(ps - TREAD_PITCH) / TREAD_PITCH * 0.05
                if best is None or score < best[0]:
                    best = (score, n, ps, m, pc)
        _, n, ps, m, pc = best
        return n, ps, m, pc, math.pi / m

    def tread_pitch(self):
        """Metres of track per animation cycle (the script's GetTreadPitch)"""
        n, ps, m, pc, step = self.tread_layout()
        return (ps + pc) / 2

    def shoe(self, b, cx, centre, normal_angle, pitch, mat, groups):
        """One track shoe: a plate on the track's inside and a grouser bar across it, standing
        out of the belt. centre: (y, z) on the pitch line; normal_angle: its outward normal's
        angle from +Y towards +Z"""
        rot = Matrix.Rotation(normal_angle - math.pi / 2, 4, "X")     # box Z -> the normal
        ny, nz = math.cos(normal_angle), math.sin(normal_angle)
        inner = -self.thickness / 2                                   # from the pitch line
        for along, h0, h1, w in ((pitch - TREAD_GAP, inner, inner + TREAD_PLATE, self.width),
                                 (TREAD_GROUSER_LEN, inner + TREAD_PLATE, inner + TREAD_PLATE + TREAD_GROUSER,
                                  self.width * 0.96)):
            mid = (h0 + h1) / 2
            b.box((w, along, h1 - h0), (cx, centre[0] + ny * mid, centre[1] + nz * mid), mat, groups, rot=rot)

    def treads(self, b, side_i, cx, mat, frame_mat, groups=()):
        """Side side_i's shoes, in four bones that model.cfg moves one pitch each cycle the way
        the track runs driving forwards: top run forwards (+Y), bottom run back, the shoes
        round each end (and the sprocket and idler with them) turning about its axle. A shoe
        hands over to the next part where a run meets an end, so cycle's end = its start."""
        n, ps, m, pc, step = self.tread_layout()
        half, z = self.wheelbase / 2, self.wheel_z
        rc = self.radius + self.thickness / 2
        bone = lambda part: (*groups, f"tread_{side_i}_{part}")
        for i in range(n):
            self.shoe(b, cx, (-half + ps * i, z + rc), math.pi / 2, ps, mat, bone("top"))
            self.shoe(b, cx, (half - ps * i, z - rc), -math.pi / 2, ps, mat, bone("bottom"))
        for k in range(m):
            a = math.pi / 2 - k * step                  # front: from the top over and down
            self.shoe(b, cx, (half + rc * math.cos(a), z + rc * math.sin(a)), a, pc, mat, bone("front"))
            a = -math.pi / 2 - k * step                 # rear: from the bottom round and up
            self.shoe(b, cx, (-half + rc * math.cos(a), z + rc * math.sin(a)), a, pc, mat, bone("rear"))
        # the idler and sprocket turn with the shoes round them: 2m teeth, a tooth a cycle
        self.gear(b, cx, half, frame_mat, bone("front"), teeth=2 * m)
        self.gear(b, cx, -half, frame_mat, bone("rear"), teeth=2 * m)

    def visual(self, b, track_mat, frame_mat, bottom_rollers=4, groups=(), tread_groups=()):
        """Treads, track frames, bottom rollers and a carrier roller on each side. `groups`:
        selections (bones) the fixed parts belong to; the treads and gears go in bones of their
        own (tread_<side>_<part>, children of the machine's in model.cfg) plus `tread_groups`"""
        half = self.wheelbase / 2
        for side_i, side in ((1, -1), (2, 1)):
            cx = side * self.x
            self.treads(b, side_i, cx, track_mat, frame_mat, tread_groups)
            b.box_between((cx - 0.2, -half + 0.1, 0.22), (cx + 0.2, half - 0.1, 2 * self.wheel_z - 0.3), frame_mat,
                          groups)
            for i in range(bottom_rollers):
                y = -half + 0.5 + (self.wheelbase - 1.0) * i / (bottom_rollers - 1)
                b.cylinder(0.14, self.width * 0.75, (cx, y, self.thickness + 0.14), frame_mat, groups, segments=12,
                           rot=X_AXIS_ROT)
            b.cylinder(0.09, self.width * 0.55, (cx, 0, 2 * self.wheel_z - self.thickness - 0.09), frame_mat,
                       groups, segments=10, rot=X_AXIS_ROT)

    def gear(self, b, x, y, mat, groups, width=0.30, teeth=8):
        """An idler/sprocket at a track end: disc, hub and teeth, turning about its axle. Its
        polygons repeat every tooth, so turning a tooth looks the same (the tread cycle)"""
        r = self.tooth_r - 0.09                 # disc; the teeth stand 9 cm proud of it
        c = (x, y, self.wheel_z)
        b.lathe_x([(-width / 2, 0.10), (-width / 2, r), (width / 2, r), (width / 2, 0.10)], c, mat, groups,
                  segments=teeth)
        b.cylinder(0.12, width + 0.1, c, mat, groups, segments=teeth, rot=X_AXIS_ROT)
        tooth = min(0.12, 2 * math.pi * r / teeth * 0.5)
        for k in range(teeth):
            a = 2 * math.pi * (k + 0.5) / teeth
            b.box((width * 0.8, tooth, 0.08), (x, y + (r + 0.03) * math.cos(a), self.wheel_z + (r + 0.03) * math.sin(a)),
                  mat, groups, rot=Matrix.Rotation(a, 4, "X"))

    CLEARANCE = 0.15    # the collision's flat bottom above the ground (the wheels carry the machine)
    RAMP_TOP = 0.8      # the ramped ends reach this high...
    RAMP_RUN = 0.9      # ...over this much length: a 34 degree slope

    def collision_profile(self):
        """The track seen from the side, (y, z), as a convex outline: a flat bottom CLEARANCE off
        the ground, ends ramped up at RAMP_TOP / RAMP_RUN from just inside the idler and
        sprocket, and the track's top. A rock meets a ramp and lifts the machine over it, as a
        real track rides up onto one, instead of a wall (the wheels are only ground probes)"""
        half, c, top = self.wheelbase / 2, self.CLEARANCE, 2 * self.wheel_z + 0.02
        y0 = half - 0.3                         # the ramps start just inside the end rollers
        y1 = y0 + self.RAMP_RUN
        zr = min(self.RAMP_TOP, top - 0.05)
        front = [(y0, c), (y1, zr), (half + self.wheel_z * 0.7, top)]
        rear = [(-y, z) for y, z in reversed(front)]
        return front + rear

    def collision(self, b, comp, names=("m_track_l", "m_track_r"), extra=()):
        """A convex prism per track in the track's outline (collision_profile)"""
        for side, name in zip((-1, 1), names):
            x0, x1 = sorted((side * (self.x - self.width / 2), side * (self.x + self.width / 2)))
            b.prism_x(self.collision_profile(), x0, x1, 0, comp(name, *extra))

    def hubs(self, b, comp):
        """Geometry LOD: the car simulation finds each wheel hub as a component of this name"""
        for sel, x, y in self.wheels():
            b.box((0.04, 0.04, 0.04), (x, y, self.wheel_z), 0, comp(f"{sel}_damper_land", "m_hubs"))

    def memory_points(self, pts):
        for sel, x, y in self.wheels():
            pts[sel] = (x, y, self.wheel_z)
            pts[sel + "_axis"] = [(x - 0.2, y, self.wheel_z), (x + 0.2, y, self.wheel_z)]
            pts[sel + "_damper_land"] = (x, y, self.wheel_z)
        pts["tread_axis"] = [(0, 0, self.wheel_z), (0, 1, self.wheel_z)]   # 1 m forwards: model.cfg Tread*

    def proxies(self, lod_obj, coll, battery_pos, battery_groups=()):
        """The attachment slots' proxies, each in its slot's selection: rollers and battery"""
        for i, (sel, x, y) in enumerate(self.wheels(), start=1):
            rv.add_proxy(lod_obj, coll, self.roller_path, (x, y, self.wheel_z), index=i, groups=(sel,))
        rv.add_proxy(lod_obj, coll, BATTERY_PROXY, battery_pos, groups=("battery", *battery_groups))

    def build_roller(self, out_path, width=0.30):
        """The wheel item's model: invisible (a 5 mm triangle at the axle; the machine draws
        its own sprockets, see GEAR_CLEARANCE) but with a geometry LOD for the item.
        Resets the scene: call before building the machine."""
        rv.reset_scene()
        dark = rv.color_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7)
        b = MeshBuilder()
        tri = [b.bm.verts.new(p) for p in ((0, 0, 0), (0, 0.005, 0), (0, 0, 0.005))]
        b.bm.faces.new(tri)
        vis = b.to_object("Roller_LOD1", [dark])
        rv.set_lod(vis, rv.LOD_VISUAL, resolution=1)
        rv.new_collection("Roller_Visual").objects.link(vis)

        g = MeshBuilder()
        g.box((width, 2 * self.wheel_r, 2 * self.wheel_r), (0, 0, 0), 0, g.component())
        geo = g.to_object("Roller_Geometry", [], triangulate_all=True)
        rv.set_component_masses(geo, {"Component01": 150})
        rv.set_lod(geo, rv.LOD_GEOMETRY, properties=(("autocenter", "0"),))
        rv.new_collection("Roller_Geometry").objects.link(geo)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        rv.turn_around()
        rv.export_p3d(out_path)


def cylinder_swing(pivot, base, mount, deg_min, deg_max):
    """A hydraulic cylinder between `base` (on the parent part) and `mount` (on a child part
    that turns about `pivot` in the (y, z) plane). Returns the barrel's turn about `base`
    (degrees, relative to the modelled pose) at the child's deg_min and deg_max, for model.cfg."""
    py, pz = pivot
    my, mz = mount[0] - py, mount[1] - pz

    def direction(deg):
        a = math.radians(deg)
        y = py + my * math.cos(a) - mz * math.sin(a)
        z = pz + my * math.sin(a) + mz * math.cos(a)
        return math.degrees(math.atan2(z - base[1], y - base[0]))

    rest = direction(0)
    return direction(deg_min) - rest, direction(deg_max) - rest


def cylinder_extension(pivot, base, mount, deg):
    """How much longer (m) the cylinder is than modelled when the child part is turned `deg`"""
    py, pz = pivot
    my, mz = mount[0] - py, mount[1] - pz
    a = math.radians(deg)
    y = py + my * math.cos(a) - mz * math.sin(a)
    z = pz + my * math.sin(a) + mz * math.cos(a)
    return math.hypot(y - base[0], z - base[1]) - math.hypot(mount[0] - base[0], mount[1] - base[1])


def cylinder_rod_axis(base, mount):
    """Memory points for the rod's slide: from `base`, 1 m along the cylinder (model.cfg's
    translation offsets are in lengths of the axis)"""
    d = (mount[0] - base[0], mount[1] - base[1])
    n = math.hypot(*d)
    return base, (base[0] + d[0] / n, base[1] + d[1] / n)


def cylinder(b, x, base, mount, barrel_len, rod_len, barrel_mat, rod_mat, barrel_bone, rod_bone,
             barrel_r=0.075, rod_r=0.04):
    """Barrel from `base` towards `mount` (in barrel_bone, which swings about the base), rod
    back from `mount` (in rod_bone: a child of the barrel's bone that slides along it, so the
    rod stays in line with the barrel; see cylinder_extension)"""
    d = (mount[0] - base[0], mount[1] - base[1])
    length = math.hypot(*d)
    u = (d[0] / length, d[1] / length)
    b.rod((x, *base), (x, base[0] + u[0] * barrel_len, base[1] + u[1] * barrel_len), barrel_r, barrel_mat,
          barrel_bone, segments=10)
    b.rod((x, mount[0] - u[0] * rod_len, mount[1] - u[1] * rod_len), (x, *mount), rod_r, rod_mat, rod_bone,
          segments=8)


def collision_object(name, parts, masses=None):
    """parts(b, comp) adds the boxes; comp(*selections) names a new component."""
    b = MeshBuilder()
    parts(b, b.component)
    obj = b.to_object(name, [], triangulate_all=True)
    if masses:
        rv.set_component_masses(obj, masses)
    # Mass groups only steer set_component_masses; drop them from the export
    for g in list(obj.vertex_groups):
        if g.name.startswith("m_"):
            obj.vertex_groups.remove(g)
    return obj


def assemble(name, visual, geometry, fire, view, memory_pts, tracks, crew_pos, battery_pos, model_path,
             crew_groups=("crewDriver",), battery_groups=(), preview=None):
    """Turn the parts into a DayZ car model: LODs, proxies, export, .blend and a preview.
    tracks: the running gear (Tracks here, or wheeled.Wheels): its proxies(), and its treads
    reported if it has any. preview = (target, camera location) for models/<name>_preview.png."""
    lod1 = rv.new_collection("LOD1_Visual")
    lod1.objects.link(visual)
    rv.set_lod(visual, rv.LOD_VISUAL, resolution=1)

    geo_c = rv.new_collection("Geometry")
    geo_c.objects.link(geometry)
    rv.set_lod(geometry, rv.LOD_GEOMETRY, properties=(("autocenter", "0"), ("class", "vehicle")))
    fire_c = rv.new_collection("FireGeometry")
    fire_c.objects.link(fire)
    rv.set_lod(fire, rv.LOD_FIRE_GEOMETRY)
    view_c = rv.new_collection("ViewGeometry")
    view_c.objects.link(view)
    rv.set_lod(view, rv.LOD_VIEW_GEOMETRY)

    for lod_obj, coll in ((visual, lod1), (view, view_c), (fire, fire_c)):
        rv.add_proxy(lod_obj, coll, CREW_PROXY, crew_pos, CREW_ROT, groups=crew_groups)
        tracks.proxies(lod_obj, coll, battery_pos, battery_groups)

    mem_c = rv.new_collection("Memory")
    memory = rv.memory_object(f"{name}_Memory", memory_pts)
    mem_c.objects.link(memory)
    rv.set_lod(memory, rv.LOD_MEMORY)

    for c in (geo_c, fire_c, view_c):
        for o in c.objects:
            o.display_type = "WIRE"

    if hasattr(tracks, "tread_layout"):
        report_treads(name, tracks)
    tris = sum(len(p.vertices) - 2 for p in visual.data.polygons)
    print(f"[{name}] visual LOD: {len(visual.data.vertices)} verts, {tris} tris")
    finish_export(name, model_path, preview)


def report_treads(name, tracks):
    n, ps, m, pc, step = tracks.tread_layout()
    print(f"[{name}] treads: {n} shoes a run at {ps:.4f} m, {m} round each end at {pc:.4f} m; model.cfg "
          f"TreadTop offset1 {ps:.4f}, TreadFront angle1 rad {-math.degrees(step):.4f}; "
          f"script GetTreadPitch {tracks.tread_pitch():.4f}")


def finish_export(name, model_path, preview):
    """Export (turned round, see the module notes), save the .blend and render a preview"""
    rv.turn_around()
    rv.export_p3d(model_path)
    rv.turn_around()
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, f"{name}.blend"))
    if preview:
        rv.render_preview(os.path.join(OUT_DIR, f"{name}_preview.png"), preview[0], preview[1],
                          visual_collections=("LOD1_Visual",))
