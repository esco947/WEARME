# CLAUDE.md — Règles du projet FitView

## Architecture du projet

```
WEARME/
├── backend/        FastAPI (Python) — port 8000
├── frontend/       Next.js 15 + TypeScript + Tailwind — port 3000
├── data/           Données statiques (catalogue.json)
├── static/         Fichiers servis par FastAPI (GLB, images)
└── simulation/     Scripts Blender headless (Phase 5+)
```

## Commandes essentielles

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Règles Backend (FastAPI / Python)

### Structure
- Tous les routers dans `backend/routers/` avec un préfixe de route clair (`/auth`, `/avatar`, `/products`)
- Tous les services métier dans `backend/services/` (logique séparée des routers)
- Les modèles SQLAlchemy dans `backend/models.py`
- Les fonctions d'auth dans `backend/auth.py`

### Conventions
- Nommer les fichiers en snake_case : `avatar_router.py`, `smpl_service.py`
- Chaque router expose un objet `router = APIRouter(prefix="...", tags=[...])`
- Dans `main.py`, inclure les routers via `app.include_router(router.router)`
- Utiliser des classes Pydantic pour tous les corps de requête et réponses
- Ne jamais retourner le `hashed_password` dans les réponses API

### Base de données
- SQLite en développement, SQLAlchemy ORM
- Fichier BDD : `backend/fitview.db` (ignoré par git)
- Les tables sont créées automatiquement au démarrage via `Base.metadata.create_all(bind=engine)`
- Toujours utiliser `Depends(get_db)` pour les sessions

### Authentification
- JWT via `python-jose`, stocké dans le header `Authorization: Bearer <token>`
- Durée de validité : 24 heures
- Utiliser `Depends(get_current_user)` pour protéger les routes
- La clé secrète est dans `SECRET_KEY` (variable d'environnement, défaut dev uniquement)

### Fichiers statiques
- Servir le dossier `static/` via `app.mount("/static", StaticFiles(...))`
- Chemin des avatars : `static/avatars/{user_id}/avatar.glb`
- Chemin des simulations : `static/simulations/{morphotype}/{garment_id}.glb`
- GLB de démo : `static/demo/avatar_demo.glb`

---

## Règles Frontend (Next.js / TypeScript)

### Structure
- Pages dans `frontend/app/` (App Router Next.js 15)
- Composants réutilisables dans `frontend/components/`
- Fonctions API centralisées dans `frontend/lib/api.ts`
- Ne pas dupliquer les appels fetch — toujours passer par `lib/api.ts`

### Conventions
- Nommer les composants en PascalCase : `AvatarScene.tsx`, `ProductCard.tsx`
- Nommer les pages `page.tsx`, les layouts `layout.tsx`
- Ajouter `'use client'` en tête de tout composant avec hooks React ou événements
- Les Server Components n'ont pas besoin de `'use client'`

### Three.js / React Three Fiber
- **Toujours** charger `AvatarScene` avec `dynamic(() => import(...), { ssr: false })` car Three.js n'est pas compatible SSR
- La caméra est positionnée à `[0, 1, 3]` avec `fov: 45`
- OrbitControls : `target=[0, 0.8, 0]`, `minDistance=1.5`, `maxDistance=5`, `enablePan=false`
- Environment preset : `"studio"` par défaut

### Authentification côté client
- JWT stocké dans `localStorage` sous la clé `fitview_token`
- Utiliser `getToken()` / `setToken()` / `removeToken()` depuis `lib/api.ts`
- Rediriger vers `/auth` si le token est absent sur les pages protégées
- Ne jamais envoyer le token dans l'URL

### Styles
- Utiliser exclusivement Tailwind CSS
- Classes utilitaires uniquement, pas de CSS custom sauf pour des cas exceptionnels
- Couleur principale : `indigo-600`
- Arrondis : `rounded-xl` (cartes), `rounded-lg` (inputs/boutons)

---

## Règles générales

### Ne pas faire
- Ne pas committer `fitview.db`, `node_modules/`, `venv/`, `.env`
- Ne pas exposer `SECRET_KEY` ou tout secret dans le code versionné
- Ne pas utiliser `any` en TypeScript sans justification
- Ne pas appeler l'API directement depuis les composants (passer par `lib/api.ts`)
- Ne pas ajouter de dépendances sans les justifier

### Données et catalogue
- Le catalogue est défini dans `data/catalogue.json`
- Format produit : `{ id, name, brand, type, sizes, color, price, thumbnail, description }`
- Types valides : `top`, `bottom`, `dress`, `jacket`
- Marques actuelles : `UrbanFit`, `ModaVerde`

### Pipeline photo (Mode Photo Précision — Phase 2.3)

Architecture du pipeline photo — tous les fichiers sont **browser-only** :

| Fichier | Rôle |
|---|---|
| `frontend/lib/pose.ts` | Singleton MediaPipe PoseLandmarker (lazy-init, GPU→CPU fallback) |
| `frontend/lib/image-preprocessing.ts` | Normalisation EXIF (OffscreenCanvas) — **toujours utiliser avant MediaPipe** |
| `frontend/lib/photo-quality.ts` | Validation qualité + cohérence géométrique des poses |
| `frontend/lib/overlay-mapping.ts` | Reprojection landmarks → canvas (`object-fit: contain`) |
| `frontend/lib/silhouette-analysis.ts` | Extraction largeurs depuis masque (médiane multi-lignes) |
| `frontend/lib/body-measurements.ts` | Estimation mensurations + mapping sliders |
| `frontend/components/PhotoPrecisionCapture.tsx` | UI du mode photo |
| `frontend/components/MeasurementConfidencePanel.tsx` | Affichage mesures + confiance |

**Règles critiques :**
- `normalizeImageOrientation(file)` → toujours appeler **avant** `detectPoseFromImage()` pour corriger l'orientation EXIF
- `computeObjectFitContainTransform()` → **toujours** utiliser pour projeter les landmarks sur le canvas (compense le letterbox `object-fit: contain`)
- `getMaskWidthAtY()` (dans `silhouette-analysis.ts`) → utiliser à la place de l'ancienne `getConstrainedWidth` (médiane multi-lignes, plus robuste)
- `extractAllMeasurements()` retourne maintenant `ExtractionResult` avec `anatomicalWarnings[]`
- Scale profil : `scaleX = scaleY * (maskH / maskW)` — corriger l'anisotropie si masque non carré
- Debug overlay : ajouter `?debug=true` à l'URL pour afficher les bornes de l'image et les lignes de scan

**Limites permanentes du mode photo :**
- Vêtements amples → sous-estimation circonférences
- Profondeur estimée à ±20% (deux photos 2D ≠ scan 3D)
- Forme jambes/bras = signal faible, confiance max ~0.5

### Phase SMPL (Phase 2+)
- Le service `smpl_service.py` est actuellement un **stub** qui retourne un GLB statique
- Pour activer la génération réelle : télécharger le modèle SMPL neutral sur smpl.is.tue.mpg.de et placer le `.pkl` dans `data/smpl_model/`
- Voir les commentaires dans `backend/services/smpl_service.py` pour l'implémentation réelle

### Phase Blender (Phase 5+)
- Les scripts de simulation sont dans `simulation/`
- Les GLB pré-simulés vont dans `static/simulations/{morphotype}/{garment_id}.glb`
- Morphotypes : `slim` (beta[0]=-1.5), `medium` (beta[0]=0), `large` (beta[0]=1.5)
- Compresser les GLB avec Draco avant de les committer : `gltf-pipeline -i input.glb -o output.glb --draco.compressionLevel 7`

---

## Workflow après chaque tâche

**À la fin de chaque tâche complétée, ouvrir automatiquement le site** pour permettre à l'utilisateur de voir les modifications :

```bash
start http://localhost:3000
```

Si la tâche concerne une page spécifique, ouvrir directement cette page (ex: `start http://localhost:3000/avatar`).
S'assurer que le backend (port 8000) et le frontend (port 3000) tournent avant d'ouvrir le navigateur.

---

## Vérification rapide (checklist)

- [ ] `GET http://localhost:8000/` retourne `{"status": "ok"}`
- [ ] `POST /auth/register` + `POST /auth/login` retournent un JWT
- [ ] `GET /products` retourne les 8 produits du catalogue
- [ ] `POST /avatar/create` (avec JWT) retourne `{ avatar_id, glb_url }`
- [ ] `http://localhost:3000` s'affiche sans erreur console
- [ ] Page `/auth` → inscription → redirection vers `/`
- [ ] Page `/catalogue` → liste des produits avec filtres
- [ ] Page `/product/[id]` → fiche produit avec bouton Essayer
- [ ] Page `/avatar` → sliders + génération → viewer 3D (après avoir placé un GLB de démo)
