# WEARME

Local virtual clothing try-on application using a parametric 3D body model.

## What it does

WEARME lets you dress a parametric 3D mannequin (powered by SMPL) with simulated garments. You can shape the body manually via sliders or estimate parameters from two reference photos, then simulate cloth draping in Blender and export the result as GLB/OBJ.

## Stack

| Layer | Technology |
|-------|-----------|
| Core | Python 3.11+ |
| 3D engine | Blender 4.x (scripting / bpy) |
| Body model | SMPL |
| Computer vision | MediaPipe Pose |
| Geometry | Trimesh · Open3D |
| Cloth simulation | Blender Cloth |
| Export | GLB / glTF / OBJ |
| Config | YAML |
| Serialisation | JSON · NPZ |

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 0 | Fondation | ✅ Complete |
| 1 | Corps manuel MVP | 🔲 Pending |
| 2 | Intégration Blender MVP | 🔲 Pending |
| 3 | Vêtement minimal | 🔲 Pending |
| 4 | Photo fitting | 🔲 Pending |
| 5 | Polish & démo | 🔲 Pending |

## Quick start

```bash
# 1. Install Python 3.11+
# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install the package in development mode
pip install -e ".[dev]"

# 4. Verify environment
python scripts/bootstrap.py

# 5. Run tests
python -m pytest tests/ -v
```

## Project layout

```
src/wearme/      Python package (core, body, vision, garments, sim, io)
configs/         YAML configuration files
data/            Body models, garments, textures, samples
blender_addon/   Blender add-on (Phase 2+)
scripts/         Utility scripts
tests/           pytest test suite
docs/            Architecture docs, roadmap, ADRs
```

## MVP scope

**Included**: torso (neck → ankles), single fixed pose, manual slider mode, 2-photo mode, 1-2 basic garments, simple 2D patterns, basic fabric presets, baked simulation, GLB/OBJ export, Blender engine.

**Excluded**: face/hair/hands, animation, body scan, advanced garment system, real-time simulation, web pipeline.

## License

MIT — see [LICENSE](LICENSE).
