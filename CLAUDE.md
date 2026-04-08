# WEARME — Instructions Claude Code

## Règle de versioning GitHub

**À chaque `git push` vers GitHub, incrémenter la version :**
- Tag Git : `vN.M` → `vN.M+1` (ex: v1.1 → v1.2)
- Mettre à jour `backend/main.py` : `version="N.M+1"`
- Commit + tag avant le push

---

## Règles de session

### 1. Toujours lancer l'app après chaque prompt
```bash
# Backend (port 8000)
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (port 5173+)
cd frontend && npm run dev -- --host
```
- Frontend : http://localhost:5173 (ou 5174/5175/5176 si port pris)
- API docs : http://localhost:8000/docs
- Health : http://localhost:8000/health

### 2. TypeScript check après chaque modification frontend
```bash
cd frontend && npx tsc --noEmit
```

### 3. Killer les vieux processus Python avant de relancer
```bash
taskkill //F //IM python.exe
```

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | FastAPI + SQLAlchemy 2.0 (sync) + SQLite |
| Auth | JWT HS256 sans expiration (python-jose + bcrypt) |
| Modèle 3D | SMPL v1.1.0 (numpy pur, 10 betas, sans chumpy) |
| Export 3D | GLB 2.0 natif numpy (pas trimesh) |
| Optimisation | Matrice de sensibilité linéaire (lstsq) |
| Frontend | React 18 + Vite 5 + TypeScript 5 |
| Routing | React Router v6 |
| State | Zustand 4 + persist |
| 3D Viewer | Three.js + @react-three/fiber v8 + @react-three/drei v9 |
| CSS | Tailwind CSS 3 (palette brand) |

---

## Architecture — packages Python

```
core/                        <- moteur SMPL, source de verite
  smpl_model.py              SMPLModel class + load_smpl(gender)
  mesh_measurements.py       measure_mesh() -> dict 6 mesures (trimesh)
  body_schema.py             SLIDERS: list[SliderDef] + SLIDER_KEYS
  beta_calibrator.py         Matrice sensibilite + solve_betas() (lstsq)
  slider_optimizer.py        optimize_betas_from_targets() -- wraps calibrator
  glb_export.py              vertices_to_glb() -- GLB natif numpy, ~1ms
  photo_optimizer.py         optimize_betas_from_photos() -- IoU + landmarks

vision/
  landmark_extractor.py      extract_landmarks() -> (33,3) + confidence
  silhouette_extractor.py    extract_silhouette() -> (N,2) contour
  camera_model.py            estimate_camera() + project_points()
  contour_fitter.py          compute_silhouette_iou() + landmark_reprojection_error()

backend/
  main.py                    FastAPI app + lifespan (prewarm SMPL + calibration)
  auth.py                    JWT sans expiration, bcrypt
  database.py                SQLAlchemy engine + session
  models.py                  User, Avatar (betas JSON + measurements_cache)
  routers/auth_router.py     POST /api/auth/register|login
  routers/user_router.py     GET /api/me
  routers/avatar_router.py   GET|PUT /api/avatar/*
  schemas/avatar.py          AvatarResponse, GenderUpdateRequest, SlidersUpdateRequest
  services/avatar_service.py get_model, compute_and_cache, update_from_sliders, get_glb
```

---

## Modèle Avatar (DB)

```python
class Avatar(Base):
    id: str               # UUID
    user_id: str          # FK -> users.id (unique)
    gender: str           # "male" | "female" seulement
    betas: str            # JSON array [10 floats] -- source de verite SMPL
    measurements_cache: str | None  # JSON dict, recalcule a chaque update
```

**Principe fondamental : les betas SMPL sont la seule source de verite.**
Les mesures sont toujours derivees du mesh (measure_mesh), jamais d'une matrice empirique.

---

## Endpoints API

```
POST /api/auth/register     { email, password } -> TokenResponse
POST /api/auth/login        { email, password } -> TokenResponse
GET  /api/me                -> UserResponse

GET  /api/avatar            -> AvatarResponse { gender, betas[10], measurements }
PUT  /api/avatar/gender     { gender } -> reset betas -> AvatarResponse
PUT  /api/avatar/sliders    { targets: {key: metres} } -> AvatarResponse
POST /api/avatar/photo-fit  multipart: front, side, height_m, gender -> AvatarResponse
GET  /api/avatar/mesh       -> GLB binary
GET  /api/avatar/measurements -> { measurements: dict }
```

---

## Architecture frontend

```
frontend/src/
  api/client.ts              Axios + intercepteur JWT, toutes fonctions API
  store/authStore.ts         { token, user, setAuth, logout }
  store/avatarStore.ts       { gender, betas, measurements, meshVersion, ... }
  components/AvatarViewer.tsx  Viewer 3D R3F + SkinTonePicker
  components/SliderPanel.tsx   6 sliders + bouton "Generer le mannequin"
  components/PhotoCapture.tsx  Upload face+profil -> photo-fit
  components/Navbar.tsx
  components/ProtectedRoute.tsx
  pages/AuthPage.tsx         Login / Register
  pages/AvatarPage.tsx       Genre + onglets Manuel/Photo + AvatarViewer
```

### Routes frontend

| Chemin | Page | Protegee |
|--------|------|----------|
| /auth  | AuthPage | Non |
| /      | redirect /avatar | Oui |
| /avatar | AvatarPage | Oui |

---

## Prechauffage au demarrage

Au lancement du backend, un thread daemon :
1. Charge les PKL SMPL male + female (load_smpl)
2. Calcule les matrices de sensibilite (get_calibration) -- ~4s par genre

Apres ~8s, chaque requete /api/avatar/sliders prend ~500ms.

---

## Performances (v1.1)

| Operation | Duree |
|-----------|-------|
| Generation mannequin (sliders) | ~500ms |
| Export GLB | ~1ms |
| Chargement avatar 3D (viewer) | ~250ms |
| Calibration SMPL cold (1 genre) | ~4s (background) |

---

## Fichiers PKL SMPL

- data/body_models/basicmodel_m_lbs_10_207_0_v1.1.0.pkl (male)
- data/body_models/basicmodel_f_lbs_10_207_0_v1.1.0.pkl (female)
- Non versionnés sur GitHub (licence SMPL), a telecharger separement.

---

## Commandes utiles

```bash
# Tests
python -m pytest tests/ -v

# TypeScript check
cd frontend && npx tsc --noEmit

# Backend dev
python -m uvicorn backend.main:app --reload --port 8000

# Frontend dev
cd frontend && npm run dev -- --host

# Reset DB (si changement de schema)
python -c "from backend.database import Base, engine; from backend.models import *; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

---

## Pieges connus

| Probleme | Cause | Solution |
|----------|-------|----------|
| Frontend sur 5174+ | Port 5173 deja pris | Utiliser le port affiche par Vite |
| uvicorn not found | Pas dans PATH | Toujours python -m uvicorn |
| SMPL cold start lent | PKL ~236 Mo | Normal, prechauffé au demarrage |
| GLB invalide (ancien code) | trimesh.export -> 420ms | Remplace par GLB numpy natif |
| "Could not validate credentials" | Token expire (ancien) | Tokens sans expiration depuis v1.1 |
| Beta[0] inverse (male) | PCA SMPL : +beta[0] = plus petit | Gere par la matrice de sensibilite |
