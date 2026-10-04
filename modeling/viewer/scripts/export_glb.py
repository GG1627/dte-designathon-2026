"""Export the existing Kintra scene for the browser, using temporary copies only.

Run in Blender's Python console:
exec(compile(open(r'FULL_PATH_TO_THIS_FILE').read(), r'FULL_PATH_TO_THIS_FILE', 'exec'))

Or: blender --background ../kintra.blend --python scripts/export_glb.py
"""

import json
from pathlib import Path
import struct

import bpy


def export_viewer_glb():
    source_scene = bpy.context.scene
    source_path = Path(bpy.data.filepath)
    if source_path.name != "kintra.blend":
        raise RuntimeError("Open the existing kintra.blend before exporting.")

    output = source_path.parent / "viewer" / "public" / "models" / "kintra.glb"
    output.parent.mkdir(parents=True, exist_ok=True)
    originals = [
        obj for obj in source_scene.objects
        if obj.visible_get() and obj.type in {"MESH", "CURVE"}
    ]
    if len(originals) != 61:
        raise RuntimeError(f"Expected the body and 60 sleeve pieces; found {len(originals)}.")

    window = bpy.context.window
    original_window_scene = window.scene if window else None
    temporary_scene = bpy.data.scenes.new("Kintra — temporary web export")
    temporary_objects = []
    temporary_data = []

    try:
        for original in originals:
            duplicate = original.copy()
            duplicate.data = original.data.copy()
            temporary_objects.append(duplicate)
            temporary_data.append(duplicate.data)
            temporary_scene.collection.objects.link(duplicate)

            if original.name == "Human - Athletic Body - Continuous Skin":
                # Preserve the mannequin silhouette with fewer browser triangles.
                decimate = duplicate.modifiers.new("Web mannequin detail", "DECIMATE")
                decimate.ratio = 0.12
            elif original.type == "CURVE":
                duplicate.data.bevel_resolution = 0 if "Knit Relief" in original.name else 1
                if "Knit Relief" in original.name:
                    # Tiny yarn tubes need fewer samples for a presentation view.
                    for spline in list(duplicate.data.splines):
                        if spline.type != "POLY":
                            raise RuntimeError("Unexpected knit spline type.")
                        points = [point.co.copy() for point in spline.points]
                        samples = points[::2]
                        if samples[-1] != points[-1]:
                            samples.append(points[-1])
                        cyclic = spline.use_cyclic_u
                        spline_type = spline.type
                        duplicate.data.splines.remove(spline)
                        replacement = duplicate.data.splines.new(spline_type)
                        replacement.points.add(len(samples) - 1)
                        replacement.use_cyclic_u = cyclic
                        for point, coordinate in zip(replacement.points, samples):
                            point.co = coordinate

        if window:
            window.scene = temporary_scene

        with bpy.context.temp_override(
            scene=temporary_scene, view_layer=temporary_scene.view_layers[0]
        ):
            depsgraph = bpy.context.evaluated_depsgraph_get()
            for duplicate in list(temporary_objects):
                # Convert curves and apply thickness/bevels on export copies.
                evaluated = duplicate.evaluated_get(depsgraph)
                mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
                temporary_data.append(mesh)
                mesh_object = bpy.data.objects.new(duplicate.name + " web", mesh)
                mesh_object.matrix_world = duplicate.matrix_world.copy()
                temporary_scene.collection.objects.link(mesh_object)
                temporary_objects.append(mesh_object)
                bpy.data.objects.remove(duplicate, do_unlink=True)
                temporary_objects.remove(duplicate)

            result = bpy.ops.export_scene.gltf(
                filepath=str(output),
                check_existing=False,
                export_format="GLB",
                use_active_scene=True,
                use_selection=False,
                export_animations=False,
                export_cameras=False,
                export_lights=False,
                export_extras=False,
                export_meshopt_compression_enable=True,
            )
            if "FINISHED" not in result:
                raise RuntimeError(f"GLB export failed: {result}")

        data = output.read_bytes()
        magic, version, length = struct.unpack_from("<III", data)
        if magic != 0x46546C67 or version != 2 or length != len(data):
            raise RuntimeError("Invalid GLB header.")
        json_length = struct.unpack_from("<I", data, 12)[0]
        document = json.loads(data[20:20 + json_length])
        if len(document.get("meshes", [])) != len(originals):
            raise RuntimeError("An object was missing from the GLB export.")
        triangle_count = sum(
            document["accessors"][primitive["indices"]]["count"] // 3
            for mesh in document["meshes"] for primitive in mesh["primitives"]
        )
        print(json.dumps({
            "file": str(output),
            "bytes": len(data),
            "meshes": len(document["meshes"]),
            "triangles": triangle_count,
            "materials": len(document.get("materials", [])),
            "extensions": document.get("extensionsUsed", []),
        }, indent=2))
    finally:
        if window:
            window.scene = original_window_scene
        for obj in temporary_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(temporary_scene)
        for data in temporary_data:
            if data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)


export_viewer_glb()
