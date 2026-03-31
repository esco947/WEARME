# WEARME — Roadmap

## Phases

### Phase 0 — Fondation ✅

**Branche** : `main` → `dev`

**Objectif** : Repo propre, structure complète, zéro code métier.

- [x] `.gitignore`, `.editorconfig`, `LICENSE`
- [x] `pyproject.toml`, `requirements/`
- [x] `configs/*.yaml` placeholders
- [x] `src/wearme/core/` — paths, constants, units, logging
- [x] `src/wearme/io/json_io.py`
- [x] `tests/test_core/` — test_paths, test_units
- [x] `scripts/bootstrap.py`
- [x] `docs/` — architecture, roadmap, git_workflow, ADR
- [x] `data/` directory structure

**Critères** : `pytest` vert · `bootstrap.py` propre · `ruff` zéro warning

---

### Phase 1 — Corps manuel MVP ✅

**Branche** : `feature/body-manual` → merged `dev`

**Objectif** : Créer, sauvegarder, charger, mesurer un corps paramétrique.

- [x] `configs/body.yaml` — limites min/max par paramètre
- [x] `src/wearme/body/body_params.py` — dataclass `BodyParameters` avec validation
- [x] `src/wearme/body/canonical_pose.py` — T-pose et A-pose
- [x] `src/wearme/body/smpl_bridge.py` — numpy LBS pur (avancé de Phase 2)
- [x] `src/wearme/body/measurements.py` — calculs via trimesh cross-sections
- [x] `src/wearme/body/manual_editor.py` — BodyEditor avec 5 sliders
- [x] `tests/test_body/` — 29 tests (body_params + measurements)
- [x] `data/samples/default_body.json`

**Critères** : 53 tests verts · ruff propre · bootstrap OK · SMPL mesh 6890 vertices

---

### Phase 2 — Intégration Blender MVP ✅

**Branche** : `feature/backend-api`

**Pré-requis** : Phase 1 complète

**Objectif** : Charger un corps dans Blender, afficher un mesh, mettre à jour, exporter.

- [x] `src/wearme/body/smpl_bridge.py` ← avancé en Phase 1
- [x] `src/wearme/sim/blender_bridge.py`
- [x] `src/wearme/io/glb_export.py`
- [x] `src/wearme/io/obj_export.py`
- [x] `blender_addon/__init__.py`
- [x] `blender_addon/panels/main_panel.py`

**Critères** : 113 tests verts · ruff propre · blender_bridge importable hors Blender

---

### Phase 3 — Vêtement minimal 🔲

**Branche** : `feature/garment-basic`

**Pré-requis** : Phase 2 complète

**Objectif** : Charger un patron, simuler le tissu, exporter habillé.

- [ ] `src/wearme/garments/pattern_schema.py`
- [ ] `src/wearme/garments/pattern_meshing.py`
- [ ] `src/wearme/garments/seam_builder.py`
- [ ] `src/wearme/garments/material_presets.py`
- [ ] `src/wearme/sim/cloth_setup.py`
- [ ] `src/wearme/sim/collision_proxy.py`
- [ ] `src/wearme/sim/bake.py`
- [ ] `data/garments/basic_tshirt.json`

---

### Phase 4 — Photo fitting 🔲

**Branche** : `feature/photo-fitting`

**Pré-requis** : Phase 1 complète (Phase 2 souhaitable)

**Objectif** : Estimer les paramètres corps depuis 2 photos.

- [ ] `src/wearme/vision/landmarks.py`
- [ ] `src/wearme/vision/segmentation.py`
- [ ] `src/wearme/vision/camera_estimation.py`
- [ ] `src/wearme/vision/photo_fitting.py`
- [ ] `scripts/fit_from_photos.py`

---

### Phase 5 — Polish & démo 🔲

**Branche** : `feature/polish`

**Pré-requis** : Phases 0-3 complètes

**Objectif** : Démo fonctionnelle bout-en-bout.
