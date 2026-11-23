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


class Tracks:
    """A crawler undercarriage: two tracks round an idler and a sprocket."""

    def __init__(self, x, width, wheelbase, radius, thickness, roller_path, roller_vis_r):
        self.x = x                      # track centre line, either side
        self.width = width              # track shoe width
        self.wheelbase = wheelbase      # idler centre to sprocket centre
        self.radius = radius            # idler/sprocket radius (the track's inner radius at the ends)
        self.thickness = thickness
        self.wheel_z = radius + thickness   # hub height: the track's bottom is on the ground
        self.wheel_r = self.wheel_z         # physics wheel radius (the roller item's config radius)
        self.roller_path = roller_path      # in-game path of the roller (wheel item) model
        self.roller_vis_r = roller_vis_r    # drawn sprocket/idler radius, inside the track

    def wheels(self):
        """(slot selection, x, y) of the four physics wheels"""
        for side_i, x in ((1, -self.x), (2, self.x)):
            for axle_i, y in ((1, self.wheelbase / 2), (2, -self.wheelbase / 2)):
                yield f"wheel_{side_i}_{axle_i}", x, y

    def visual(self, b, track_mat, frame_mat, bottom_rollers=4, groups=()):
        """Belts, track frames, bottom rollers and a carrier roller on each side; `groups`:
        selections (bones) they belong to"""
        half = self.wheelbase / 2
        for side in (-1, 1):
            cx = side * self.x
            b.band_x(rv.stadium(self.wheelbase, self.radius, self.wheel_z, segments=12), self.thickness,
                     cx - self.width / 2, cx + self.width / 2, track_mat, groups)
            b.box_between((cx - 0.2, -half + 0.1, 0.22), (cx + 0.2, half - 0.1, 2 * self.wheel_z - 0.3), frame_mat,
                          groups)
            for i in range(bottom_rollers):
                y = -half + 0.5 + (self.wheelbase - 1.0) * i / (bottom_rollers - 1)
                b.cylinder(0.14, self.width * 0.75, (cx, y, self.thickness + 0.14), frame_mat, groups, segments=12,
                           rot=X_AXIS_ROT)
            b.cylinder(0.09, self.width * 0.55, (cx, 0, 2 * self.wheel_z - self.thickness - 0.09), frame_mat,
                       groups, segments=10, rot=X_AXIS_ROT)

    def collision(self, b, comp, names=("m_track_l", "m_track_r"), extra=()):
        """A box per track, clear of the ground: the wheels carry the machine"""
        half = self.wheelbase / 2 + self.radius * 0.6
        for side, name in zip((-1, 1), names):
            x0, x1 = sorted((side * (self.x - self.width / 2), side * (self.x + self.width / 2)))
            b.box_between((x0, -half, 0.25), (x1, half, 2 * self.wheel_z + 0.02), 0, comp(name, *extra))

    def hubs(self, b, comp):
        """Geometry LOD: the car simulation finds each wheel hub as a component of this name"""
        for sel, x, y in self.wheels():
            b.box((0.04, 0.04, 0.04), (x, y, self.wheel_z), 0, comp(f"{sel}_damper_land", "m_hubs"))

    def memory_points(self, pts):
        for sel, x, y in self.wheels():
            pts[sel] = (x, y, self.wheel_z)
            pts[sel + "_axis"] = [(x - 0.2, y, self.wheel_z), (x + 0.2, y, self.wheel_z)]
            pts[sel + "_damper_land"] = (x, y, self.wheel_z)

    def proxies(self, lod_obj, coll, battery_pos, battery_groups=()):
        """The attachment slots' proxies, each in its slot's selection: rollers and battery"""
        for i, (sel, x, y) in enumerate(self.wheels(), start=1):
            rv.add_proxy(lod_obj, coll, self.roller_path, (x, y, self.wheel_z), index=i, groups=(sel,))
        rv.add_proxy(lod_obj, coll, BATTERY_PROXY, battery_pos, groups=("battery", *battery_groups))

    def build_roller(self, out_path, width=0.30):
        """The sprocket/idler model drawn at each physics wheel (the wheel item's model).
        Resets the scene: call before building the machine."""
        rv.reset_scene()
        dark = rv.color_material("steel_dark", (0.16, 0.16, 0.16), 0.5, 0.7)
        b = MeshBuilder()
        r = self.roller_vis_r
        b.lathe_x([(-width / 2, 0.10), (-width / 2, r), (width / 2, r), (width / 2, 0.10)], (0, 0, 0), 0, segments=16)
        b.cylinder(0.12, width + 0.1, (0, 0, 0), 0, segments=12, rot=X_AXIS_ROT)
        for k in range(8):   # sprocket teeth
            a = 2 * math.pi * k / 8
            b.box((width * 0.8, 0.12, 0.08), (0, (r + 0.03) * math.cos(a), (r + 0.03) * math.sin(a)), 0,
                  rot=Matrix.Rotation(a, 4, "X"))
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


def cylinder(b, x, base, mount, barrel_len, rod_len, barrel_mat, rod_mat, barrel_bone, rod_bone,
             barrel_r=0.075, rod_r=0.04):
    """Barrel from `base` towards `mount` (in barrel_bone), rod back from `mount` (in rod_bone)"""
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
    preview = (target, camera location) for models/<name>_preview.png."""
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

    tris = sum(len(p.vertices) - 2 for p in visual.data.polygons)
    print(f"[{name}] visual LOD: {len(visual.data.vertices)} verts, {tris} tris")

    rv.turn_around()
    rv.export_p3d(model_path)
    rv.turn_around()
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, f"{name}.blend"))
    if preview:
        rv.render_preview(os.path.join(OUT_DIR, f"{name}_preview.png"), preview[0], preview[1],
                          visual_collections=("LOD1_Visual",))
