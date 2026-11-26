"""Running gear for the Big Machines that drive on real wheels (the combine harvester): the
four wheels the vanilla car simulation drives and steers on, drawn by the wheel items in
their slots, and the bones and memory points the suspension needs. crawler.assemble() takes a
Wheels in place of a Tracks.

Bones, as vanilla cars have them (the hatchback's ODOL: wheel_1_1 <- susp_hub_1_1 <-
susp_arm_1_1). The game never moves a wheel bone up and down itself: the suspension source
(damper_X_Y) moves a parent bone, and the wheel bone only spins. So each wheel has three:
    susp_<w>    rides the suspension: translation along <w>_damper_axis (1 m, straight up)
    steer_<w>   child of susp_<w>: turns about the vertical through the hub
    wheel_<w>   child of steer_<w>: spins about <w>_axis; holds the wheel item's proxy
where <w> is wheel_<side>_<axle>, side 1 = left, axle 1 = front, by where the wheel is on the
machine (config.cpp maps the car simulation's axles onto them: a combine steers with its back
wheels). model.cfg: BM_Wheeled in BigMachines/model.cfg.

Damper phase (the engine's damper_X_Y source): 0 = pushed all the way up (travelMaxUp), 1 =
hanging all the way down (travelMaxDown); the modelled position is phase travelMaxUp /
(travelMaxUp + travelMaxDown) (vanilla's truck: initPhase 0.4828 = 0.14 / 0.29). Wheels(...)
prints the offsets model.cfg needs.
"""

import math
import os

from mathutils import Matrix

import rv
from rv import MeshBuilder, X_AXIS_ROT

BATTERY_PROXY = "dz\\vehicles\\parts\\battery_truck.p3d"


class Axle:
    """A pair of wheels: y along the machine, x of each wheel's centre either side, the wheel
    item (radius, width, model path) and the suspension travel (config.cpp Suspension)"""

    def __init__(self, index, y, x, radius, width, wheel_path, travel_up, travel_down):
        self.index = index              # the <axle> in wheel_<side>_<axle>: 1 front, 2 back
        self.y = y
        self.x = x
        self.radius = radius
        self.width = width
        self.wheel_path = wheel_path
        self.travel_up = travel_up
        self.travel_down = travel_down

    @property
    def hub_z(self):
        """The wheel's centre at rest: its tyre on the ground"""
        return self.radius

    def damper_phase(self):
        return self.travel_up / (self.travel_up + self.travel_down)


class Wheels:
    def __init__(self, axles):
        self.axles = axles

    def wheels(self):
        """(selection wheel_<side>_<axle>, x, y, axle) for all four"""
        for axle in self.axles:
            for side_i, x in ((1, -axle.x), (2, axle.x)):
                yield f"wheel_{side_i}_{axle.index}", x, axle.y, axle

    def memory_points(self, pts):
        for sel, x, y, axle in self.wheels():
            z = axle.hub_z
            pts[sel] = (x, y, z)
            pts[sel + "_axis"] = [(x - 0.2, y, z), (x + 0.2, y, z)]
            pts[sel + "_steer_axis"] = [(x, y, z), (x, y, z + 1.0)]
            pts[sel + "_damper_axis"] = [(x, y, z), (x, y, z + 1.0)]
            pts[sel + "_damper_land"] = (x, y, z)

    def hubs(self, b, comp):
        """Geometry LOD: the car simulation finds each wheel hub as a component of this name"""
        for sel, x, y, axle in self.wheels():
            b.box((0.04, 0.04, 0.04), (x, y, axle.hub_z), 0, comp(f"{sel}_damper_land", "m_hubs"))

    def proxies(self, lod_obj, coll, battery_pos, battery_groups=()):
        """The attachment slots' proxies, each in its wheel's bone: wheels and battery"""
        for i, (sel, x, y, axle) in enumerate(self.wheels(), start=1):
            rv.add_proxy(lod_obj, coll, axle.wheel_path, (x, y, axle.hub_z), index=i, groups=(sel,))
        rv.add_proxy(lod_obj, coll, BATTERY_PROXY, battery_pos, groups=("battery", *battery_groups))

    def report(self, name):
        for axle in self.axles:
            print(f"[{name}] axle {axle.index}: damper translation offset0 {axle.travel_up} offset1 "
                  f"{-axle.travel_down} (phase {axle.damper_phase():.4f} = as modelled); wheel radius "
                  f"{axle.radius}, width {axle.width}")


def tyre_profile(radius, width, rim_r, shoulder=0.06):
    """Closed (x offset, radius) outline of a tyre's cross-section for MeshBuilder.lathe_x:
    bead to bead round the outside, rounded shoulders"""
    h = width / 2
    s = min(shoulder, h * 0.4)
    return [(-h + 0.01, rim_r), (-h, radius - s * 1.6), (-h + s * 0.4, radius - s * 0.4), (-h + s, radius),
            (h - s, radius), (h - s * 0.4, radius - s * 0.4), (h, radius - s * 1.6), (h - 0.01, rim_r)]


def build_wheel(out_path, radius, width, rim_r, lugs, tyre_mat_name="tyre_rubber", rim_mat_name="rim_paint",
                rim_color=(0.75, 0.72, 0.62), lug_depth=0.035, rim_weathered=False):
    """A wheel item's model, centred on its axle (the proxy point): a tyre with angled tread
    bars (a chevron, the halves staggered), a dished rim and hub. Geometry LOD for the item.
    rim_weathered: the rim in rv.weathered_material(rim_mat_name) (tools/make_weathering.py).
    Resets the scene: call before building the machine."""
    rv.reset_scene()
    rubber = rv.color_material(tyre_mat_name, (0.035, 0.035, 0.035), 0.9, 0.0)
    if rim_weathered:
        rim = rv.weathered_material(rim_mat_name, rim_color, 0.5, 0.4)
    else:
        rim = rv.color_material(rim_mat_name, rim_color, 0.5, 0.4)
    b = MeshBuilder()
    body_r = radius - lug_depth
    b.lathe_x(tyre_profile(body_r, width, rim_r), (0, 0, 0), 0, (), segments=max(24, lugs))
    h = width / 2
    for k in range(lugs):
        for half, stagger in ((-1, 0.0), (1, 0.5)):
            a = 2 * math.pi * (k + stagger) / lugs
            bar_len = h * 0.95
            rot = Matrix.Rotation(a, 4, "X") @ Matrix.Rotation(math.radians(half * 28), 4, "Z")
            loc = (half * bar_len / 2, (body_r + lug_depth / 2 - 0.004) * math.cos(a),
                   (body_r + lug_depth / 2 - 0.004) * math.sin(a))
            b.box((bar_len, 0.055, lug_depth + 0.008), loc, 0, (), rot=rot)
    # rim: a dished disc inside the beads, a centre hub with studs
    b.lathe_x([(-h + 0.04, 0.08), (-h + 0.04, rim_r), (h - 0.04, rim_r), (h - 0.04, rim_r - 0.03),
               (0.02, rim_r - 0.05), (0.06, 0.12), (0.06, 0.08)], (0, 0, 0), 1, (), segments=24)
    b.cylinder(0.12, width * 0.55, (0, 0, 0), 1, (), segments=12, rot=X_AXIS_ROT)
    for k in range(6):
        a = 2 * math.pi * k / 6
        b.cylinder(0.018, 0.04, (width * 0.28, 0.085 * math.cos(a), 0.085 * math.sin(a)), 1, (), segments=6,
                   rot=X_AXIS_ROT)
    vis = b.to_object("Wheel_LOD1", [rubber, rim])
    rv.set_lod(vis, rv.LOD_VISUAL, resolution=1)
    rv.new_collection("Wheel_Visual").objects.link(vis)

    g = MeshBuilder()
    g.box((width, 2 * radius, 2 * radius), (0, 0, 0), 0, g.component())
    geo = g.to_object("Wheel_Geometry", [], triangulate_all=True)
    rv.set_component_masses(geo, {"Component01": 120})
    rv.set_lod(geo, rv.LOD_GEOMETRY, properties=(("autocenter", "0"),))
    rv.new_collection("Wheel_Geometry").objects.link(geo)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rv.turn_around()
    rv.export_p3d(out_path)
