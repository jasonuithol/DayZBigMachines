"""Shared helpers for building DayZ (RV engine) models in Blender with the Arma 3 Object
Builder add-on. Imported by the per-machine build scripts in this folder.

Conventions: 1 Blender unit = 1 metre, Blender +X right, +Y forward, +Z up. The add-on
writes P3D axes as (x, z, y), so Blender +Y becomes the model's forward (+Z in game).
Vertex groups become named selections; each convex part of a collision LOD is a
"ComponentNN" selection (MeshBuilder.component numbers them).
"""

import math

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

A3OB_MODULE = "bl_ext.user_default.Arma3ObjectBuilder"

# LOD type codes from the add-on's utilities/data.py (LOD class)
LOD_VISUAL = "0"
LOD_VIEW_PILOT = "2"
LOD_SHADOW = "4"
LOD_GEOMETRY = "6"
LOD_GEOMETRY_PHYSX = "8"
LOD_MEMORY = "9"
LOD_VIEW_GEOMETRY = "14"
LOD_FIRE_GEOMETRY = "15"

X_AXIS_ROT = Matrix.Rotation(math.radians(90), 4, "Y")  # turns a Z-aligned cylinder onto X


def enable_addon():
    addon_utils.enable(A3OB_MODULE, default_set=False)
    if not hasattr(bpy.ops.a3ob, "export_p3d"):
        raise RuntimeError(f"Arma 3 Object Builder add-on ({A3OB_MODULE}) is not installed")


def reset_scene():
    # Clear the startup scene by hand: read_factory_settings would also unload the add-on
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.cameras, bpy.data.lights, bpy.data.collections, bpy.data.worlds):
        for block in list(coll):
            coll.remove(block)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def color_material(name, color, roughness=0.6, metallic=0.0, rvmat=""):
    """Material with a procedural colour texture (#(argb,8,8,3)color(...)) in game; the
    Blender colour is only for previews."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    props = mat.a3ob_properties_material
    props.texture_type = "CUSTOM"
    props.color_raw = "#(argb,8,8,3)color(%.3f,%.3f,%.3f,1.0,co)" % color
    props.material_path = rvmat
    return mat


def texture_material(name, game_path, png_path, rvmat=""):
    """Material with a real texture: `game_path` (e.g. BigMachines\\data\\x_ca.paa) in game,
    the source PNG in Blender previews, its alpha cut out"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png_path, check_existing=True)
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.6
    mat.blend_method = "CLIP"
    props = mat.a3ob_properties_material
    props.texture_type = "CUSTOM"
    props.color_raw = game_path
    props.material_path = rvmat
    return mat


class MeshBuilder:
    """Accumulates parts into one bmesh, tracking material and selections per part.
    Everything but decals has UVs at 0 (flat colour textures)."""

    def __init__(self):
        self.bm = bmesh.new()
        self.groups = {}  # selection name -> list of verts
        self.components = 0
        self.face_uvs = []  # (face, [(u, v) per corner]) for decals

    def _tag(self, verts, mat_index, groups):
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = mat_index
        if isinstance(groups, str):
            groups = (groups,)
        for group in groups or ():
            self.groups.setdefault(group, []).extend(verts)

    def component(self, *groups):
        """Selection names for the next convex collision part: ComponentNN plus extras."""
        self.components += 1
        return ("Component%02d" % self.components, *groups)

    def box(self, size, loc, mat_index=0, groups=(), rot=None):
        m = Matrix.Translation(loc)
        if rot is not None:
            m = m @ rot
        m = m @ Matrix.Diagonal((*size, 1.0))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._tag(res["verts"], mat_index, groups)
        return res["verts"]

    def box_between(self, lo, hi, mat_index=0, groups=()):
        """Axis-aligned box from corner lo to corner hi."""
        lo, hi = Vector(lo), Vector(hi)
        return self.box(hi - lo, (lo + hi) / 2, mat_index, groups)

    def cylinder(self, radius, depth, loc, mat_index=0, groups=(), segments=12, rot=None, radius2=None):
        m = Matrix.Translation(loc)
        if rot is not None:
            m = m @ rot
        res = bmesh.ops.create_cone(
            self.bm, cap_ends=True, segments=segments,
            radius1=radius, radius2=radius if radius2 is None else radius2, depth=depth, matrix=m,
        )
        self._tag(res["verts"], mat_index, groups)
        return res["verts"]

    def rod(self, a, b, radius, mat_index=0, groups=(), segments=8):
        """Cylinder from point a to point b."""
        a, b = Vector(a), Vector(b)
        d = b - a
        rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        return self.cylinder(radius, d.length, (a + b) / 2, mat_index, groups, segments, rot)

    def prism_x(self, profile, x0, x1, mat_index=0, groups=()):
        """Extrude a closed (y, z) polygon from x = x0 to x = x1 (capped)."""
        bm = self.bm
        left = [bm.verts.new((x0, y, z)) for y, z in profile]
        right = [bm.verts.new((x1, y, z)) for y, z in profile]
        n = len(profile)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((left[i], left[j], right[j], right[i]))
        bm.faces.new(list(reversed(left)))
        bm.faces.new(right)
        verts = left + right
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in verts for f in v.link_faces}))
        self._tag(verts, mat_index, groups)
        return verts

    def prism_z(self, profile, z0, z1, mat_index=0, groups=()):
        """Extrude a closed (x, y) polygon from z = z0 to z = z1 (capped)."""
        bm = self.bm
        bottom = [bm.verts.new((x, y, z0)) for x, y in profile]
        top = [bm.verts.new((x, y, z1)) for x, y in profile]
        n = len(profile)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
        bm.faces.new(list(reversed(bottom)))
        bm.faces.new(top)
        verts = bottom + top
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in verts for f in v.link_faces}))
        self._tag(verts, mat_index, groups)
        return verts

    def band_x(self, loop, thickness, x0, x1, mat_index=0, groups=()):
        """A closed belt (a track) around a closed (y, z) loop, `thickness` thick outwards,
        from x = x0 to x = x1. The loop must run counter-clockwise seen from +X."""
        bm = self.bm
        n = len(loop)
        pts = [Vector(p) for p in loop]
        outer = []
        for i in range(n):
            t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
            normal = Vector((t.y, -t.x))  # outward for a counter-clockwise loop
            outer.append(pts[i] + normal * thickness)
        rings = []
        for i in range(n):
            rings.append((bm.verts.new((x0, *pts[i])), bm.verts.new((x0, *outer[i])),
                          bm.verts.new((x1, *outer[i])), bm.verts.new((x1, *pts[i]))))
        for i in range(n):
            a, b = rings[i], rings[(i + 1) % n]
            for k in range(4):
                k2 = (k + 1) % 4
                bm.faces.new((a[k], b[k], b[k2], a[k2]))
        verts = [v for r in rings for v in r]
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in verts for f in v.link_faces}))
        self._tag(verts, mat_index, groups)
        return verts

    def lathe_x(self, profile, center, mat_index=0, groups=(), segments=20):
        """Revolve a closed (x_offset, radius) profile around the X axis."""
        bm = self.bm
        center = Vector(center)
        rings = []
        for x_off, r in profile:
            ring = []
            for k in range(segments):
                a = 2 * math.pi * k / segments
                ring.append(bm.verts.new(center + Vector((x_off, r * math.cos(a), r * math.sin(a)))))
            rings.append(ring)
        for j in range(len(rings)):
            r0, r1 = rings[j], rings[(j + 1) % len(rings)]
            for k in range(segments):
                k2 = (k + 1) % segments
                bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
        verts = [v for r in rings for v in r]
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in verts for f in v.link_faces}))
        self._tag(verts, mat_index, groups)
        return verts

    def decal(self, center, right, up, width, height, mat_index, groups=(), uv=(0, 0, 1, 1)):
        """A flat quad showing a texture: centred on `center`, `right` and `up` unit vectors
        as seen from the side it faces (its normal is right x up). Put it a few mm off the
        surface it sits on. uv = (u0, v0, u1, v1), v up."""
        c, r, u = Vector(center), Vector(right) * (width / 2), Vector(up) * (height / 2)
        corners = [c - r - u, c + r - u, c + r + u, c - r + u]
        u0, v0, u1, v1 = uv
        return self._uv_quad(corners, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat_index, groups)

    def decal_strip(self, path, bottom, top, offset, mat_index, groups=(), uv=(0, 0, 1, 1)):
        """A decal following a wall seen from above: `path` is (x, y) points along the wall,
        left to right as seen from outside, from height `bottom` to `top`, standing `offset`
        out from it (to the viewer's side). The texture stretches along the path by length."""
        pts = [Vector((x, y, 0)) for x, y in path]
        outs = []
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            outs.append(p + Vector((d.y, -d.x, 0)) * offset)  # right of the direction of travel
        lengths = [0.0]
        for i in range(1, len(pts)):
            lengths.append(lengths[-1] + (pts[i] - pts[i - 1]).length)
        u0, v0, u1, v1 = uv
        verts = []
        for i in range(len(pts) - 1):
            ua = u0 + (u1 - u0) * lengths[i] / lengths[-1]
            ub = u0 + (u1 - u0) * lengths[i + 1] / lengths[-1]
            a, b = outs[i], outs[i + 1]
            corners = [Vector((a.x, a.y, bottom)), Vector((b.x, b.y, bottom)), Vector((b.x, b.y, top)),
                       Vector((a.x, a.y, top))]
            verts += self._uv_quad(corners, [(ua, v0), (ub, v0), (ub, v1), (ua, v1)], mat_index, groups)
        return verts

    def _uv_quad(self, corners, uvs, mat_index, groups):
        verts = [self.bm.verts.new(c) for c in corners]
        face = self.bm.faces.new(verts)
        self.face_uvs.append((face, uvs))
        self._tag(verts, mat_index, groups)
        return verts

    def to_object(self, name, materials, triangulate_all=False):
        # P3D faces must be tris or quads; collision LODs are fully triangulated so
        # convexity is unambiguous.
        uv_layer = self.bm.loops.layers.uv.verify()
        for face, uvs in self.face_uvs:
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv
        faces = [f for f in self.bm.faces if triangulate_all or len(f.verts) > 4]
        bmesh.ops.triangulate(self.bm, faces=faces, quad_method="BEAUTY", ngon_method="BEAUTY")
        if not triangulate_all:
            # Not in collision LODs: parts that touch would be welded into one non-convex component
            bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=0.0001)
        self.bm.verts.index_update()
        group_indices = {g: sorted({v.index for v in vs if v.is_valid}) for g, vs in self.groups.items()}
        self.bm.normal_update()
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        obj = bpy.data.objects.new(name, mesh)
        for mat in materials:
            mesh.materials.append(mat)
        for g, idx in group_indices.items():
            if idx:
                obj.vertex_groups.new(name=g).add(idx, 1.0, "REPLACE")
        return obj


def stadium(length, radius, z, segments=10):
    """Counter-clockwise (seen from +X) (y, z) loop around two circles of `radius`, centred
    `length` apart on the Y axis at height z: a crawler track's outline."""
    pts = []
    half = length / 2
    for i in range(segments + 1):          # front end, bottom -> top
        a = -math.pi / 2 + math.pi * i / segments
        pts.append((half + radius * math.cos(a), z + radius * math.sin(a)))
    for i in range(segments + 1):          # rear end, top -> bottom
        a = math.pi / 2 + math.pi * i / segments
        pts.append((-half + radius * math.cos(a), z + radius * math.sin(a)))
    return pts


def add_proxy(lod_obj, collection, path, loc, rot_deg=(0, 0, 0), index=1, groups=()):
    """A proxy triangle parented to a LOD object; the add-on merges it in on export. The
    right angle marks the origin, the short leg points forward (+Y), the long leg up."""
    name = f"proxy_{path.split(chr(92))[-1]}_{index}_{len(collection.objects)}"
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0, 0, 0), (0, 0, 0.1), (0, 0.05, 0)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = [math.radians(a) for a in rot_deg]
    obj.parent = lod_obj
    obj.hide_render = True
    for g in groups:
        obj.vertex_groups.new(name=g).add([0, 1, 2], 1.0, "REPLACE")
    props = obj.a3ob_properties_object_proxy
    props.is_a3_proxy = True
    props.proxy_path = path
    props.proxy_index = index
    collection.objects.link(obj)
    return obj


def memory_object(name, points):
    """Memory LOD: loose vertices. `points` maps a selection name to one point or a list of
    points (an axis is two)."""
    verts, groups = [], {}
    for sel, pts in points.items():
        if isinstance(pts[0], (int, float)):
            pts = [pts]
        groups[sel] = list(range(len(verts), len(verts) + len(pts)))
        verts.extend(pts)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [])
    obj = bpy.data.objects.new(name, mesh)
    for sel, idx in groups.items():
        obj.vertex_groups.new(name=sel).add(idx, 1.0, "REPLACE")
    return obj


def set_lod(obj, lod, resolution=0, properties=()):
    props = obj.a3ob_properties_object
    props.is_a3_lod = True
    props.lod = lod
    props.resolution = resolution
    for name, value in properties:
        prop = props.properties.add()
        prop.name = name
        prop.value = value


def set_component_masses(obj, masses):
    """Spread each selection's mass (kg) evenly over its vertices; `masses` maps selection
    name -> kg. Vertices in no listed selection get nothing."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.verts.layers.float.new("a3ob_mass")
    deform = bm.verts.layers.deform.verify()
    index = {g.name: g.index for g in obj.vertex_groups}
    members = {name: [v for v in bm.verts if index[name] in v[deform]] for name in masses}
    for v in bm.verts:
        v[layer] = 0.0
    for name, kg in masses.items():
        for v in members[name]:
            v[layer] += kg / len(members[name])
    bm.to_mesh(obj.data)
    bm.free()


def new_collection(name):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def turn_around():
    """Rotate every LOD (mesh data and proxy children) 180 degrees about Z. The exporter
    writes Blender (x, y, z) as P3D (-x, z, -y), so a model built facing +Y would face the
    game's -Z; DayZ vehicles face +Z. Call before export and again after (it undoes itself)."""
    rot = Matrix.Rotation(math.pi, 4, "Z")
    for obj in bpy.data.objects:
        if obj.parent is None and obj.type == "MESH" and obj.a3ob_properties_object.is_a3_lod:
            obj.data.transform(rot)
            obj.data.update()
            for child in obj.children:
                child.location = rot @ child.location
                child.rotation_euler.z += math.pi


def export_p3d(path):
    bpy.ops.a3ob.export_p3d(
        filepath=path,
        use_selection=False,
        validate_lods=True,
        validate_lods_warning_errors=False,
        lod_collisions="FAIL",
    )


def render_preview(path, target, cam_loc, lens=35, size=(1400, 1000), visual_collections=()):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = size
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.6, 0.65, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    scene.world = world

    preview = new_collection("Preview")
    ground = bpy.data.meshes.new("ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=30)
    gbm.to_mesh(ground)
    gbm.free()
    g_obj = bpy.data.objects.new("PreviewGround", ground)
    ground.materials.append(color_material("preview_ground", (0.35, 0.32, 0.28), 0.95))
    preview.objects.link(g_obj)

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(-40))
    preview.objects.link(sun)

    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.location = cam_loc
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    preview.objects.link(cam)
    scene.camera = cam

    keep = set(visual_collections) | {"Preview"}
    for c in bpy.data.collections:
        c.hide_render = c.name not in keep

    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


class Wall:
    """A flat face of a machine to put details on, in its own coordinates: s along `right`,
    t along `up` (as seen from outside), n out of the face (normal = right x up). `center`
    is a point on the face; `groups`: the selections (bone) the details belong to."""

    SEAM = 0.012        # width of a panel seam
    SEAM_DEPTH = 0.005

    def __init__(self, b, center, right, up, groups=()):
        self.b = b
        self.c = Vector(center)
        self.r = Vector(right).normalized()
        self.u = Vector(up).normalized()
        self.n = self.r.cross(self.u)
        self.groups = groups
        self.rot = Matrix((self.r, self.u, self.n)).transposed().to_4x4()

    def point(self, s, t, n=0.0):
        return self.c + self.r * s + self.u * t + self.n * n

    def plate(self, s0, t0, s1, t1, depth, mat, n0=0.0, tilt=0.0):
        """A box over s0..s1, t0..t1 standing n0..n0+depth off the face; `tilt` (degrees)
        turns it about its own s axis (a louvre)"""
        rot = self.rot @ Matrix.Rotation(math.radians(tilt), 4, "X")
        loc = self.point((s0 + s1) / 2, (t0 + t1) / 2, n0 + depth / 2)
        return self.b.box((abs(s1 - s0), abs(t1 - t0), depth), loc, mat, self.groups, rot=rot)

    def seams(self, s0, t0, s1, t1, mat):
        """The outline of a panel: four thin strips"""
        w, d = self.SEAM, self.SEAM_DEPTH
        self.plate(s0, t0, s1, t0 + w, d, mat)
        self.plate(s0, t1 - w, s1, t1, d, mat)
        self.plate(s0, t0, s0 + w, t1, d, mat)
        self.plate(s1 - w, t0, s1, t1, d, mat)

    def door(self, s0, t0, s1, t1, mat, hinge="left", handle=True):
        """An access door: seams, two hinges on the `hinge` edge (left/right/top), a handle
        by the opposite edge"""
        self.seams(s0, t0, s1, t1, mat)
        h = 0.07
        if hinge in ("left", "right"):
            s = s0 + 0.03 if hinge == "left" else s1 - 0.03
            for t in (t0 + 0.12, t1 - 0.12 - h):
                self.plate(s - 0.02, t, s + 0.02, t + h, 0.02, mat)
            if handle:
                s = s1 - 0.09 if hinge == "left" else s0 + 0.09
                tm = (t0 + t1) / 2
                self.plate(s - 0.015, tm - 0.06, s + 0.015, tm + 0.06, 0.03, mat)
        else:
            for s in (s0 + 0.12, s1 - 0.12 - h):
                self.plate(s, t1 - 0.05, s + h, t1 - 0.01, 0.02, mat)
            if handle:
                sm = (s0 + s1) / 2
                self.plate(sm - 0.06, t0 + 0.05, sm + 0.06, t0 + 0.08, 0.03, mat)

    def grille(self, s0, t0, s1, t1, back_mat, slat_mat, pitch=0.045, frame=0.03, tilt=35.0):
        """Louvred grille: a dark backing, a frame, and slats running along s, tilted down"""
        self.plate(s0, t0, s1, t1, 0.006, back_mat)
        f = frame
        self.plate(s0, t0, s1, t0 + f, 0.035, slat_mat)
        self.plate(s0, t1 - f, s1, t1, 0.035, slat_mat)
        self.plate(s0, t0, s0 + f, t1, 0.035, slat_mat)
        self.plate(s1 - f, t0, s1, t1, 0.035, slat_mat)
        t = t0 + f + pitch / 2
        while t < t1 - f - pitch / 3:
            self.plate(s0 + f, t - 0.008, s1 - f, t + 0.008, 0.04, slat_mat, n0=0.004, tilt=tilt)
            t += pitch

    def mesh(self, s0, t0, s1, t1, back_mat, bar_mat, pitch=0.05):
        """A guard of crossed bars (radiator mesh) over a dark backing"""
        self.plate(s0, t0, s1, t1, 0.006, back_mat)
        s = s0
        while s <= s1 + 1e-6:
            self.plate(s - 0.006, t0, s + 0.006, t1, 0.02, bar_mat)
            s += pitch
        t = t0
        while t <= t1 + 1e-6:
            self.plate(s0, t - 0.006, s1, t + 0.006, 0.026, bar_mat)
            t += pitch

    def decal(self, s, t, width, height, mat, uv=(0, 0, 1, 1), n=0.004):
        """A texture centred at (s, t), `n` off the face"""
        return self.b.decal(self.point(s, t, n), self.r, self.u, width, height, mat, self.groups, uv)

    def light(self, s, t, radius, lens_mat, body_mat, depth=0.08):
        """A round work light facing out of the face"""
        rot = self.rot
        self.b.cylinder(radius, depth, self.point(s, t, depth / 2), body_mat, self.groups, segments=12, rot=rot)
        self.b.cylinder(radius * 0.8, 0.01, self.point(s, t, depth + 0.004), lens_mat, self.groups, segments=12,
                        rot=rot)
