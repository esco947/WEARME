# WEARME — Instructions Claude Code

## Règles de session

### 1. Toujours lancer l'app après chaque prompt
Après chaque modification, démarrer les deux serveurs en background :

```bash
# Backend (port 8000) — utiliser python -m uvicorn (pas uvicorn direct)
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (port 5173, peut basculer sur 5174+ si le port est pris)
cd frontend && npm run dev -- --host
```

- Frontend : http://localhost:5173 (ou 5174)
- API docs : http://localhost:8000/docs
- Health : http://localhost:8000/health

### 2. TypeScript check après chaque modification frontend
```bash
cd frontend && npx tsc --noEmit
```

---

## Stack

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend framework | FastAPI | latest |
| ORM | SQLAlchemy 2.0 (sync) | latest |
| Migrations | Alembic | latest |
| Base de données | SQLite (`data/wearme.db`) | — |
| Auth | python-jose (JWT HS256) + bcrypt | 30 min expiry |
| Modèle 3D corps | SMPL v1.1.0 (numpy pur, sans chumpy) | `src/wearme/body/` |
| Frontend framework | React 18 + Vite 5 + TypeScript 5 | — |
| Routing frontend | React Router v6 | — |
| State management | Zustand 4 + persist | — |
| 3D viewer | Three.js 0.183 + @react-three/fiber v8 + @react-three/drei v9 | — |
| Pose detection | @mediapipe/tasks-vision 0.10.14 | CDN WASM |
| CSS | Tailwind CSS 3 | custom brand palette |

---

## Architecture backend

```
backend/
├── main.py              FastAPI app, CORS, routers
├── auth.py              JWT (get_current_user), bcrypt
├── database.py          SQLAlchemy engine + session factory
├── models.py            User, Avatar, Garment (ORM)
├── seed.py              Seed catalogue JSON → DB
├── routers/
│   ├── auth_router.py   POST /api/auth/register, /api/auth/login
│   ├── user_router.py   GET  /api/me
│   ├── avatar_router.py GET/PUT /api/avatar, /measurements, /from-photo, /mesh
│   ├── garment_router.py GET /api/garments, /api/garments/{id}
│   └── fitting_router.py POST /api/fitting/{garment_id}
├── schemas/
│   ├── auth.py          LoginRequest, RegisterRequest, TokenResponse, UserResponse
│   ├── avatar.py        AvatarResponse, AvatarUpdateRequest, MeasurementsResponse, PhotoEstimationResponse
│   ├── garment.py       GarmentResponse, GarmentListResponse
│   └── fitting.py       FittingResponse
└── services/
    ├── avatar_service.py   get_measurements(), get_glb_bytes()  ← SMPL bridge
    ├── photo_service.py    estimate_betas_from_photo()  ← fallback backend photo scan
    ├── garment_service.py  list_garments(), get_garment()
    └── fitting_service.py  recommend_size()
```

### SMPL body model
- Fichiers pkl : `data/body_models/` (neutral + male)
- Female → fallback automatique vers neutral (pkl female absent)
- Chargement paresseux, mis en cache après premier appel (~10-20 s)
- `src/wearme/body/smpl_bridge.py` : `load_model_data(gender)`, `generate_vertices(params, model_data)`
- `src/wearme/body/measurements.py` : `compute_measurements(params, model_data)`
- `generate_vertices()` retourne des vertices à échelle naturelle (~1.7 m pour betas=0)
- **`avatar_service.get_glb_bytes()`** rescale le mesh à `avatar.height_m` exact après génération

---

## Architecture frontend

```
frontend/src/
├── main.tsx             ReactDOM.createRoot + BrowserRouter
├── App.tsx              Routes (auth, catalogue, avatar, fitting, product)
├── api/
│   └── client.ts        Axios instance, intercepteur JWT, toutes les fonctions API
├── components/
│   ├── AvatarViewer.tsx          Viewer 3D R3F (skin tone, lighting, OrbitControls)
│   ├── PhotoPrecisionCapture.tsx Composant photo 3-étapes (upload → process → results)
│   ├── MeasurementConfidencePanel.tsx  Tableau confiance par mesure
│   ├── Navbar.tsx
│   ├── ProtectedRoute.tsx
│   ├── ProductCard.tsx
│   └── ErrorBoundary.tsx
├── pages/
│   ├── AuthPage.tsx       Login / Register
│   ├── AvatarPage.tsx     Éditeur avatar (onglets Manuel + Photo scan)
│   ├── CataloguePage.tsx  Catalogue vêtements
│   ├── ProductPage.tsx    Détail produit
│   └── FittingPage.tsx    Recommandation taille
├── lib/
│   ├── bodyParamsMapping.ts  bodyParamsToSmplBetas(), smplBetasToBodyParams()
│   ├── pose.ts               MediaPipe PoseLandmarker singleton, detectPoseFromImage()
│   ├── body-measurements.ts  estimateBodyParams() → BodyParamsEstimate
│   └── photo-quality.ts      validatePhotoQuality() → QualityReport
├── store/
│   ├── authStore.ts     Zustand + persist → { token, user, setAuth, logout }
│   └── avatarStore.ts   Zustand → { avatar, measurements, loading, setAvatar, reset }
└── types/
    ├── index.ts         Toutes les interfaces TypeScript (User, Avatar, BodyParams…)
    └── r3f-global.d.ts  Fix namespace JSX pour @react-three/fiber v8
```

### Routes frontend
| Chemin | Page | Protégée |
|--------|------|----------|
| `/auth` | AuthPage | Non |
| `/catalogue` | CataloguePage | Oui |
| `/catalogue/:id` | ProductPage | Oui |
| `/avatar` | AvatarPage | Oui |
| `/fitting/:id` | FittingPage | Oui |

---

## Endpoints API

### Auth
```
POST /api/auth/register  { email, password } → TokenResponse
POST /api/auth/login     { email, password } → TokenResponse
GET  /api/me             → UserResponse
```

### Avatar
```
GET  /api/avatar               → AvatarResponse
PUT  /api/avatar               { gender?, betas?, height_m?, weight_kg? } → AvatarResponse
GET  /api/avatar/measurements  → { height_m, chest_m, waist_m, hips_m }
POST /api/avatar/from-photo    multipart: front_photo, side_photo?, height_m, weight_kg → PhotoEstimationResponse
GET  /api/avatar/mesh          → GLB binary (model/gltf-binary)
```

### Catalogue & Fitting
```
GET  /api/garments       → { items: Garment[], total: int }
GET  /api/garments/{id}  → Garment
POST /api/fitting/{id}   → FittingResponse { recommended_size, available_sizes, measurements }
```

---

## Conventions SMPL / BodyParams

### Betas (10 composantes PCA)
| Index | Effet empirique (modèle neutral) |
|-------|----------------------------------|
| b[0]  | Non utilisé — hauteur gérée par rescaling backend |
| b[1]  | Corpulence **INVERSÉ** : + = mince, − = gros |
| b[2]  | Longueur membres (+ = plus longs) |
| b[3]  | Largeur épaules + poitrine |
| b[4]  | Hanches **INVERSÉ** : − = plus larges |
| b[5]  | Volume global (− = plus plein) |
| b[6]  | Ventre proéminent (+ = plus rond) |
| b[7]  | Épaisseur jambes (− = plus épaisses) |
| b[8]  | Longueur bras secondaire |
| b[9]  | Hanches secondaire |

### BodyParams → betas (bodyParamsMapping.ts)
- Sliders en [-1, +1], betas clampés à [-3.5, 3.5]
- `weight_kg` et `height_m` → BMI → `fatness` → drive b[1], b[5], b[6]
- `bodyParamsToSmplBetas(p)` → `number[]`
- `smplBetasToBodyParams(b, height_m, weight_kg)` → `BodyParams`
- `DEFAULT_BODY_PARAMS` : 1.75 m / 70 kg / tout à 0

### Skin tones (AvatarViewer.tsx)
6 teintes : `very-light #FDDBB4` → `light` → `medium` → `tan` → `dark` → `very-dark #3B1F0F`
Stockées dans `localStorage` (clé `wearme_skin_tone`).

---

## Photo scan client-side (MediaPipe)

### Pipeline (PhotoPrecisionCapture.tsx)
1. Upload photo de face (obligatoire) + profil (optionnel) + taille/poids
2. `detectPoseFromImage(imgEl)` → `PoseResult` (landmarks normalisés + segmentation mask)
3. `validatePhotoQuality(pose, view)` → erreurs bloquantes / avertissements
4. `estimateBodyParams(front, side, height_m, weight_kg)` → `BodyParamsEstimate`
5. Affichage canvas unique (photo + squelette dessinés ensemble)

### Règle critique des distances
Les landmarks sont normalisés (0–1) mais X et Y ont des échelles différentes pour images non-carrées.
**Toujours convertir en pixels avant de diviser :**
```typescript
// Horizontal : utiliser imgW
const widthPx = normXDist * imgW
// Vertical : utiliser imgH
const bfPx = bodyFill * imgH
// → metres = (widthPx / bfPx) * height_m
```

### Modèle MediaPipe
WASM depuis CDN : `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm`
Modèle depuis CDN Google Storage (pas besoin de fichier local).
Premier chargement : ~25 Mo, ~10 s. Prewarm au mount avec `prewarmPoseLandmarker()`.

---

## Tailwind — Palette brand

```javascript
brand: {
  50:  '#f0f4ff',
  100: '#e0eaff',
  500: '#4f6ef7',   // primary
  600: '#3b54e8',
  700: '#2f44cc',
}
```
Utiliser `bg-brand-500`, `text-brand-600`, `border-brand-400`, etc.

---

## Commandes utiles

```bash
# Tests backend
python -m pytest tests/ -v

# Linter backend
python -m ruff check backend/ src/ tests/

# TypeScript check frontend
cd frontend && npx tsc --noEmit

# Migration DB
python -m alembic upgrade head

# Seed catalogue
python backend/seed.py

# Backend dev
python -m uvicorn backend.main:app --reload --port 8000

# Frontend dev
cd frontend && npm run dev -- --host
```

---

## Pièges connus

| Problème | Cause | Solution |
|----------|-------|----------|
| `uvicorn` not found | Pas dans PATH | Toujours `python -m uvicorn` |
| Frontend sur 5174+ | Port 5173 déjà pris | Killer les vieux `node.exe` ou utiliser le port affiché |
| SMPL premier chargement lent | pkl 236 Mo ASCII protocol 0 | Normal ~10-20 s, mise en cache ensuite |
| Avatar rendu "Modèle SMPL requis" | Token JWT tronqué par split('_') | Passer `token` directement, pas en clé composite |
| Overlay squelette décalé | CSS `object-contain` letterboxing | Dessiner img + squelette sur un seul `<canvas>` |
| Mesures photos fausses | Distances X-normalized ≠ Y-normalized pour images non-carrées | Convertir en pixels réels avant calcul |
| GLB silencieusement invalide | Backend 500 → Blob non-GLB | Valider les 4 magic bytes `glTF` avant `URL.createObjectURL` |
| Female SMPL absent | Seuls neutral + male disponibles | Fallback auto vers neutral dans `_get_model()` |
| `Property 'primitive' does not exist` | R3F v8 JSX namespace | `src/types/r3f-global.d.ts` + `"types": ["@react-three/fiber"]` dans tsconfig |
