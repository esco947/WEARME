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

### Phase 1 — Corps manuel MVP 🔲

**Branche** : `feature/body-manual`

**Objectif** : Créer, sauvegarder, charger, mesurer un corps paramétrique.

- [ ] `configs/body.yaml` — limites min/max par paramètre
- [ ] `src/wearme/body/body_params.py` — dataclass `BodyParameters` avec validation
- [ ] `src/wearme/body/measurements.py` — calculs de mensurations
- [ ] `src/wearme/body/canonical_pose.py` — pose fixe T/A
- [ ] `src/wearme/body/manual_editor.py` — logique slider
- [ ] `tests/test_body/` — test_body_params, test_measurements
- [ ] `data/samples/default_body.json`

**Critères** : création · validation · JSON aller-retour · calculs cohérents · tests verts

---

### Phase 2 — Intégration Blender MVP 🔲

**Branche** : `feature/blender-bridge`

**Pré-requis** : Phase 1 complète

**Objectif** : Charger un corps dans Blender, afficher un mesh, mettre à jour, exporter.

- [ ] `src/wearme/body/smpl_bridge.py`
- [ ] `src/wearme/sim/blender_bridge.py`
- [ ] `src/wearme/io/glb_export.py`
- [ ] `src/wearme/io/obj_export.py`
- [ ] `blender_addon/__init__.py`
- [ ] `blender_addon/panels/main_panel.py`

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
