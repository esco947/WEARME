# WEARME — Architecture technique

## Vue d'ensemble

WEARME est une application **locale** d'essayage virtuel. Le pipeline complet va de la saisie des mensurations (manuelle ou photo) à l'export d'un mesh 3D habillé.

```
[Utilisateur]
     │
     ├── Mode manuel (sliders)
     │       └─→ BodyParameters ──┐
     │                            │
     └── Mode photo (2 images)    ├─→ SMPL mesh ──→ Blender cloth sim ──→ Export GLB/OBJ
             └─→ PhotoFitting ────┘
```

## Package Python : `src/wearme/`

### `wearme.core`
Utilitaires partagés sans dépendances métier.

| Module | Rôle |
|--------|------|
| `paths.py` | Constantes `pathlib.Path` centralisées (PROJECT_ROOT, DATA_DIR, …) |
| `constants.py` | Constantes métier (limites corps, APP_NAME, VERSION) |
| `units.py` | Conversions SI : cm ↔ m, mm ↔ m, inches ↔ m |
| `logging_config.py` | `setup_logging(level)` — handler stdout avec format timestampé |

### `wearme.body` (Phase 1+)
Modèle corporel paramétrique.

| Module | Rôle |
|--------|------|
| `body_params.py` | Dataclass `BodyParameters` avec validation des limites |
| `measurements.py` | Calculs tour de poitrine, taille, hanches, etc. |
| `canonical_pose.py` | Définition de la pose T/A fixe (angles articulaires) |
| `manual_editor.py` | Logique de modification par slider |
| `smpl_bridge.py` | Interface avec le modèle SMPL (Phase 2) |

### `wearme.vision` (Phase 4+)
Estimation de pose et fitting photo.

| Module | Rôle |
|--------|------|
| `landmarks.py` | Wrapper MediaPipe Pose |
| `segmentation.py` | Extraction de silhouette |
| `camera_estimation.py` | Estimation des paramètres caméra |
| `photo_fitting.py` | Optimisation des paramètres corps depuis 2 photos |

### `wearme.garments` (Phase 3+)
Patrons et matériaux.

| Module | Rôle |
|--------|------|
| `pattern_schema.py` | Schéma JSON de patron 2D |
| `pattern_meshing.py` | Triangulation 2D → 3D |
| `seam_builder.py` | Construction des coutures |
| `material_presets.py` | Presets tissu (cotton, jersey, denim…) |

### `wearme.sim` (Phase 2+)
Bridge Blender et simulation tissu.

| Module | Rôle |
|--------|------|
| `blender_bridge.py` | API bpy — chargement mesh, mise à jour |
| `cloth_setup.py` | Configuration simulation tissu Blender |
| `collision_proxy.py` | Mesh proxy décimé pour collisions |
| `bake.py` | Bake de la simulation |

### `wearme.io`
Sérialisation.

| Module | Rôle |
|--------|------|
| `json_io.py` | `load_json` / `save_json` génériques |
| `glb_export.py` | Export GLB/glTF (Phase 2+) |
| `obj_export.py` | Export OBJ (Phase 2+) |

## Structure des données

```
data/
├── body_models/    # fichiers SMPL (.pkl, .npz) — non versionnés
├── garments/       # patrons JSON + meshes
├── textures/       # textures de base
└── samples/        # photos d'exemple, bodies test
```

Formats de sérialisation :

| Fichier | Format | Contenu |
|---------|--------|---------|
| `body_params.json` | JSON | Paramètres utilisateur lisibles |
| `body_latent.npz` | NPZ | Vecteur latent SMPL |
| `body_mesh.glb` | GLB | Mesh rendu |
| `body_collision.obj` | OBJ | Mesh proxy simplifié |
| `pattern.json` | JSON | Patron vêtement 2D |

## Blender addon

Le répertoire `blender_addon/` contient un addon Blender minimal (Phase 2+).
Blender fournit son propre interpréteur Python avec `bpy` — ne pas installer
`bpy` via pip. Les scripts Blender injectent le package `wearme` via `sys.path`.

## Stack complète

| Couche | Technologie |
|--------|-------------|
| Cœur | Python 3.11+ |
| 3D engine | Blender 4.x (scripting) |
| Corps | SMPL |
| Vision | MediaPipe Pose |
| Géométrie | Trimesh · Open3D |
| Simulation | Blender Cloth |
| Export | GLB / glTF / OBJ |
| Config | YAML |
| Sérialisation | JSON · NPZ |
