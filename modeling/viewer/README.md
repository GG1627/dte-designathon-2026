# Kintra model viewer

A standalone React + Three.js presentation viewer for the existing `../kintra.blend` model.

## Run locally

Requires Node.js 22.12+ (or 20.19+).

```sh
cd modeling/viewer
npm install
npm run dev
```

Open **http://localhost:5173**. Drag to orbit and scroll or pinch to zoom. The viewer includes full-body and knee-detail framing, front/side/back views, zoom and rotation buttons, reset, auto-rotation, fullscreen presentation, and a GLB download. Auto-rotation starts off and respects reduced-motion preferences.

The dev server is accessible on the local network, so another device on the same Wi-Fi can use `http://YOUR_COMPUTER_IP:5173`. Keep the server running during the demo.

## Build for sharing

```sh
npm run build
npm run preview
```

Preview opens at **http://localhost:4173**. The `dist/` directory is a static website that can be hosted on a static hosting service. It supports deployment under a subdirectory. Serve it over HTTP; opening `index.html` directly will not load the model correctly.

All assets, including the GLB and its mesh decoder, are served locally. The viewer has no CDN, remote font, or environment-map dependency, which keeps a local presentation usable without internet once dependencies are installed.

## Model and export

The browser asset is `public/models/kintra.glb` (about 4.3 MB, 61 meshes, 575,700 triangles). It contains the mannequin and all existing sleeve pieces, including knit relief, straps, buckles, orange supports, and wraparound bands. Materials retain their original base colors and roughness. Blender-specific procedural shading and subsurface effects are not reproduced exactly by glTF.

The export uses meshopt compression. The bundled Three.js meshopt decoder handles it without an external download. Export-only copies reduce mannequin polygons and tiny yarn-tube detail; the source Blender model is preserved.

To refresh the GLB after editing the Blender model, open `kintra.blend` and run this in Blender's Python Console, replacing the path:

```python
path = r'C:\full\path\to\modeling\viewer\scripts\export_glb.py'
exec(compile(open(path, encoding='utf-8').read(), path, 'exec'))
```

Or, with Blender on your command path, run from this folder:

```sh
blender --background ../kintra.blend --python scripts/export_glb.py
```

The script exports only visible model objects, applies thickness and bevels on temporary mesh copies, and removes those copies afterward. It does not save or modify the source `.blend` file.
