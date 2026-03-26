# FitView — Plan d'implémentation étape par étape

## Vue d'ensemble du projet

**Objectif :** Plateforme web d'essayage virtuel de vêtements en 3D.
**Stack :** Next.js (frontend) + FastAPI (backend) + React Three Fiber (3D) + SMPL (avatar) + Blender (simulation tissu)
**Durée estimée :** 3 mois (12 semaines)

---

## Phase 0 — Préparation de l'environnement (Jours 1–3)

### 0.1 Installer les prérequis système
- Node.js (v18+) et npm
- Python 3.10+ et pip
- Blender 4.x (pour la simulation tissu, à installer plus tard mais prévoir l'espace)
- Git pour le versioning
- Un éditeur (VS Code recommandé)

### 0.2 Créer la structure du projet
- Créer le dossier racine `fitview/`
- Initialiser un repo Git
- Créer un `.gitignore` (ignorer `node_modules/`, `__pycache__/`, `.env`, `static/simulations/`, `data/smpl_model/`)

### 0.3 Créer les sous-dossiers de données
- `data/smpl_model/` — pour les fichiers pkl du modèle SMPL
- `data/garments/` — pour les meshes de vêtements (OBJ + JSON)
- `data/catalogue.json` — données produits
- `static/simulations/` — GLB pré-calculés (avec sous-dossiers par morphotype)

---

## Phase 1 — Squelette backend FastAPI (Semaine 1)

### Étape 1.1 — Initialiser le backend
- Créer le dossier `backend/`
- Créer un environnement virtuel Python : `python -m venv venv`
- Installer les dépendances de base :
  ```
  pip install fastapi uvicorn sqlalchemy python-jose bcrypt pydantic
  ```
- Créer `backend/main.py` avec une route de test `GET /` → `{"status": "ok"}`
- Vérifier que `uvicorn main:app --reload --port 8000` démarre correctement

### Étape 1.2 — Configurer la base de données SQLite
- Créer `backend/database.py` avec SQLAlchemy + moteur SQLite (`sqlite:///./fitview.db`)
- Créer `backend/models.py` avec les modèles :
  - **User** : id, email, hashed_password, created_at
  - **Avatar** : id, user_id (FK), betas (JSON string des 10 paramètres SMPL), glb_path, created_at
  - **Garment** : id, name, brand, type, obj_path, thumbnail_url
  - **Simulation** : id, avatar_id (FK), garment_id (FK), glb_path, status (pending/done/error), created_at
- Créer les tables automatiquement au démarrage de l'app

### Étape 1.3 — Implémenter l'authentification JWT
- Créer `backend/auth.py` :
  - Fonction `hash_password(password)` avec bcrypt
  - Fonction `verify_password(plain, hashed)` avec bcrypt
  - Fonction `create_access_token(data, expires_delta)` avec python-jose
  - Fonction `get_current_user(token)` — décoder le JWT et retourner le user
- Créer `backend/routers/auth_router.py` :
  - `POST /auth/register` — email + password → crée le user → retourne le JWT
  - `POST /auth/login` — email + password → vérifie → retourne le JWT
- Tester avec curl ou Postman : inscription puis connexion

### Étape 1.4 — Configurer le CORS
- Dans `main.py`, ajouter `CORSMiddleware` pour autoriser `http://localhost:3000`
- Autoriser les headers `Authorization` et `Content-Type`

**Livrable de la semaine 1 :** Un backend FastAPI fonctionnel avec auth JWT, BDD SQLite, et CORS configuré.

---

## Phase 2 — Module avatar SMPL (Semaine 2)

### Étape 2.1 — Installer les dépendances IA/3D
```
pip install smplx torch trimesh pyrender numpy
```
- Télécharger le modèle SMPL neutral depuis le site officiel (smpl.is.tue.mpg.de) — nécessite une inscription académique
- Placer les fichiers `.pkl` dans `data/smpl_model/`

### Étape 2.2 — Créer le service SMPL
- Créer `backend/services/smpl_service.py` :
  - Fonction `generate_avatar_mesh(betas: list[float]) -> trimesh.Trimesh`
    - Charger le modèle SMPL neutral
    - Appliquer les betas (10 paramètres de forme)
    - Pose neutre (bras légèrement écartés = A-pose ou T-pose)
    - Retourner le mesh
  - Fonction `export_to_glb(mesh, output_path: str)`
    - Convertir le mesh trimesh en scène
    - Exporter en GLB avec `trimesh.exchange.gltf.export_glb()`
- Tester en standalone : générer un GLB et l'ouvrir dans un viewer en ligne (gltf-viewer.donmccurdy.com)

### Étape 2.3 — Créer les routes avatar
- Créer `backend/routers/avatar_router.py` :
  - `POST /avatar/create` — reçoit `{ betas: [float x10] }` + JWT
    - Appelle `smpl_service.generate_avatar_mesh(betas)`
    - Exporte le GLB dans `static/avatars/{user_id}/avatar.glb`
    - Enregistre le chemin en BDD
    - Retourne `{ avatar_id, glb_url }`
  - `GET /avatar/{avatar_id}` — retourne les infos de l'avatar
  - `GET /avatar/{avatar_id}/glb` — sert le fichier GLB
- Tester avec curl : envoyer des betas, vérifier que le GLB est valide

### Étape 2.4 — Servir les fichiers statiques
- Configurer FastAPI pour servir `static/` en fichiers statiques (`app.mount("/static", StaticFiles(...))`)
- Vérifier qu'on peut accéder à un GLB via `http://localhost:8000/static/avatars/.../avatar.glb`

**Livrable de la semaine 2 :** Route API qui prend des paramètres morphologiques et retourne un avatar 3D au format GLB.

---

## Phase 3 — Frontend Next.js + première page 3D (Semaine 3)

### Étape 3.1 — Initialiser le frontend
- Depuis la racine du projet :
  ```
  npx create-next-app@latest frontend --typescript --app --tailwind
  ```
- Installer les dépendances 3D :
  ```
  npm install @react-three/fiber @react-three/drei three
  npm install -D @types/three
  ```
- Vérifier que `npm run dev` démarre sur `localhost:3000`

### Étape 3.2 — Page d'authentification (`/auth`)
- Créer `frontend/app/auth/page.tsx`
- Deux formulaires : inscription et connexion
- Au submit : appel `fetch("http://localhost:8000/auth/register")` ou `/auth/login`
- Stocker le JWT dans `localStorage` (suffisant pour un MVP)
- Redirection vers `/` après login réussi
- Créer un hook `useAuth()` ou un context React pour gérer l'état d'authentification

### Étape 3.3 — Composant AvatarScene.tsx (le cœur 3D)
- Créer `frontend/components/AvatarScene.tsx` :
  - Importer `Canvas` de `@react-three/fiber`
  - Importer `OrbitControls`, `useGLTF`, `Environment`, `ContactShadows` de `@react-three/drei`
  - Composant enfant `AvatarModel({ glbUrl })` qui charge le GLB avec `useGLTF`
  - Canvas avec :
    - Caméra positionnée devant le mannequin (`position: [0, 1, 3]`)
    - Lumière ambiante + directionnelle
    - `Environment preset="studio"` pour un éclairage PBR
    - `ContactShadows` au sol
    - `OrbitControls` (rotation, zoom, pas de pan)
  - Marqué `'use client'` obligatoirement
- **IMPORTANT :** Charger ce composant avec `dynamic(() => import(...), { ssr: false })` car Three.js ne fonctionne pas côté serveur

### Étape 3.4 — Page création avatar (`/avatar`)
- Créer `frontend/app/avatar/page.tsx`
- Interface avec des sliders React pour les 10 paramètres SMPL :
  - Corpulence générale (beta 0 — le plus important)
  - Taille (beta 1)
  - Largeur des épaules, etc.
  - Les labels doivent être compréhensibles ("Corpulence", "Taille", "Épaules"...) pas les noms techniques
- Bouton "Générer mon avatar"
- Au clic : `POST /avatar/create` avec les betas
- Quand le GLB revient : l'afficher dans `<AvatarScene glbUrl={url} />`
- L'utilisateur voit son avatar en 3D et peut tourner autour

### Étape 3.5 — Tester le flux complet auth → avatar
- S'inscrire → se connecter → aller sur `/avatar` → bouger les sliders → générer → voir le modèle 3D
- Corriger les bugs d'intégration frontend/backend (CORS, JWT, URLs)

**Livrable de la semaine 3 :** L'utilisateur peut créer un compte, ajuster des sliders morphologiques, et voir son avatar 3D dans le navigateur.

---

## Phase 4 — Catalogue de produits (Semaine 4)

### Étape 4.1 — Créer les données du catalogue
- Créer `data/catalogue.json` avec 5 à 10 vêtements fictifs :
  ```json
  {
    "id": "tshirt-basic-01",
    "name": "T-shirt Essentiel",
    "brand": "UrbanFit",
    "type": "top",
    "sizes": ["S", "M", "L", "XL"],
    "color": "Blanc",
    "price": 29.99,
    "thumbnail": "/images/tshirt-basic-01.jpg",
    "description": "T-shirt en coton bio, coupe droite"
  }
  ```
- Inventer 2 ou 3 marques fictives
- Mélanger les types : T-shirts, pantalons, robes, vestes
- Créer les images thumbnails (photos libres de droits ou mockups simples)

### Étape 4.2 — Routes catalogue backend
- Créer `backend/routers/catalogue_router.py` :
  - `GET /products` — retourne la liste des produits (avec filtres optionnels par type, marque)
  - `GET /products/{id}` — retourne un produit par son ID
- Charger les données depuis `catalogue.json` au démarrage

### Étape 4.3 — Page catalogue frontend (`/catalogue`)
- Créer `frontend/app/catalogue/page.tsx`
- Grille de cartes produit (`ProductCard.tsx`)
- Chaque carte : image, nom, marque, prix, bouton "Voir"
- Filtres optionnels (par type de vêtement, par marque)
- Au clic sur une carte → navigation vers `/product/[id]`

### Étape 4.4 — Page fiche produit (`/product/[id]`)
- Créer `frontend/app/product/[id]/page.tsx`
- Afficher : grande image, nom, marque, prix, description, tailles
- Bouton principal : **"Essayer en 3D"** → redirige vers `/tryon/[productId]`
- Ce bouton n'est actif que si l'utilisateur est connecté et a un avatar

### Étape 4.5 — Navigation globale
- Créer un layout commun avec navbar :
  - Logo "FitView"
  - Liens : Accueil, Catalogue, Mon Avatar
  - Bouton Connexion / Déconnexion
- Page d'accueil (`/`) avec un hero + appel à l'action vers le catalogue

**Livrable de la semaine 4 :** Un catalogue navigable avec fiches produits et un bouton "Essayer en 3D".

---

## Phase 5 — Simulation tissu dans Blender (Semaines 5–6)

### Étape 5.1 — Créer les vêtements de base dans Blender (GUI)
- Ouvrir Blender et créer manuellement 3 vêtements simples :
  - Un T-shirt (panneau tissu moulé autour du torse)
  - Un pantalon simple (deux cylindres tissu autour des jambes)
  - Une robe basique (panneau tissu long)
- Exporter chaque vêtement seul en OBJ dans `data/garments/`
- Prendre le temps de bien modéliser — ces assets seront réutilisés

### Étape 5.2 — Script de simulation Blender headless
- Créer `simulation/cloth_sim.py` — script Python exécutable par Blender :
  1. Importer le mannequin SMPL (OBJ exporté par smplx)
  2. Importer le panneau vêtement (OBJ)
  3. Ajouter un modifier Cloth au vêtement avec des propriétés réalistes (masse, rigidité, friction)
  4. Ajouter un modifier Collision au mannequin
  5. Lancer la simulation (ex : 50 frames pour laisser le tissu tomber)
  6. Appliquer le modifier (figer le résultat)
- Créer `simulation/export_glb.py` :
  1. Joindre mannequin + vêtement simulé en une scène
  2. Exporter en GLB
- Tester en ligne de commande :
  ```
  blender --background --python simulation/cloth_sim.py -- --body body.obj --garment tshirt.obj --output result.glb
  ```

### Étape 5.3 — Pré-simuler les morphotypes
- Générer 3 à 5 corps SMPL avec des betas différents :
  - Morphotype **slim** : beta[0] = -1.5
  - Morphotype **medium** : beta[0] = 0
  - Morphotype **large** : beta[0] = 1.5
  - (Optionnel : ajouter petit/grand en variant beta[1])
- Pour chaque morphotype × chaque vêtement :
  - Lancer la simulation Blender
  - Stocker le GLB résultant dans `static/simulations/{morphotype}/{garment_id}.glb`
- Cela donne environ 9 à 15 fichiers GLB pré-calculés

### Étape 5.4 — Compresser les GLB avec Draco
- Installer `gltf-pipeline` :
  ```
  npm install -g gltf-pipeline
  ```
- Pour chaque GLB :
  ```
  gltf-pipeline -i input.glb -o output.glb --draco.compressionLevel 7
  ```
- Objectif : passer de 5–20 Mo à 1–3 Mo par fichier

**Livrable de la semaine 6 :** 3 vêtements simulés sur 3–5 morphotypes, GLB compressés prêts à être servis.

---

## Phase 6 — Scène d'essayage complète (Semaine 7)

### Étape 6.1 — Logique de matching morphotype
- Créer `backend/services/matching_service.py` :
  - Fonction `find_closest_morphotype(user_betas) -> str`
  - Calculer la distance euclidienne entre les betas de l'utilisateur et ceux des morphotypes pré-simulés
  - Retourner le morphotype le plus proche (slim, medium, large...)

### Étape 6.2 — Route d'essayage backend
- Créer `backend/routers/tryon_router.py` :
  - `POST /tryon/request` — reçoit `{ user_id, garment_id }` + JWT
    1. Récupérer les betas de l'avatar de l'utilisateur
    2. Trouver le morphotype le plus proche
    3. Vérifier si le GLB existe : `static/simulations/{morphotype}/{garment_id}.glb`
    4. Si oui → retourner `{ status: "ready", glb_url: "..." }`
    5. Si non → retourner `{ status: "unavailable" }`
  - `GET /tryon/status/{job_id}` — pour la V2 avec simulation à la demande

### Étape 6.3 — Page d'essayage frontend (`/tryon/[productId]`)
- Créer `frontend/app/tryon/[productId]/page.tsx`
- Au chargement :
  1. Appeler `POST /tryon/request` avec le user_id et le garment_id
  2. Pendant le chargement : afficher un loader animé ("Préparation de votre essayage...")
  3. Quand le GLB URL arrive : charger `<AvatarScene glbUrl={url} />`
- Contrôles utilisateur :
  - Rotation (clic + glisser) — géré par OrbitControls
  - Zoom (molette) — géré par OrbitControls
  - Bouton "Retour au catalogue"
  - Informations du produit à côté de la scène 3D (nom, taille, marque)

### Étape 6.4 — Améliorer la qualité visuelle
- Ajouter un environnement HDRI via `Environment preset="studio"` ou `preset="city"`
- Configurer les ombres de contact (`ContactShadows`)
- Ajuster les limites d'OrbitControls :
  - `minDistance={1.5}` / `maxDistance={5}` pour empêcher de traverser le modèle
  - `target={[0, 0.8, 0]}` pour centrer sur le torse
  - `enablePan={false}` pour garder le modèle centré
- Ajouter un fond neutre ou un gradient

**Livrable de la semaine 7 :** L'utilisateur peut cliquer "Essayer en 3D" et voir son avatar habillé dans une scène 3D interactive.

---

## Phase 7 — Intégration end-to-end (Semaine 8)

### Étape 7.1 — Tester le parcours complet
Suivre ce scénario de bout en bout et corriger tous les bugs :
1. Arriver sur la page d'accueil
2. S'inscrire (email + mot de passe)
3. Se connecter
4. Aller sur `/avatar` → ajuster les sliders → générer l'avatar → le voir en 3D
5. Aller sur `/catalogue` → parcourir les produits
6. Cliquer sur un produit → voir la fiche
7. Cliquer "Essayer en 3D" → voir l'avatar habillé
8. Revenir au catalogue → essayer un autre vêtement
9. Se déconnecter et se reconnecter → vérifier que l'avatar est conservé

### Étape 7.2 — Gestion d'erreurs
- GLB non trouvé → message "Simulation non disponible pour votre morphologie"
- Utilisateur non connecté qui clique "Essayer" → redirection vers `/auth`
- Utilisateur sans avatar → redirection vers `/avatar`
- Erreur réseau → message d'erreur avec bouton "Réessayer"
- Fichier GLB corrompu → fallback avec un message

### Étape 7.3 — Responsive basique
- La scène 3D doit s'adapter en taille (mobile = plein écran, desktop = 60% de la page)
- Le catalogue doit passer en 1 colonne sur mobile
- La navbar doit avoir un menu burger sur mobile

### Étape 7.4 — Nettoyage du code
- Factoriser les appels API dans un fichier `frontend/lib/api.ts`
- Centraliser la gestion du JWT
- Ajouter des types TypeScript pour toutes les réponses API
- Commenter le code des parties critiques (smpl_service, cloth_sim)

**Livrable de la semaine 8 :** Parcours utilisateur complet fonctionnel, sans bugs bloquants, responsive.

---

## Phase 8 — Reconstruction depuis photo (Semaines 9–10)

### Étape 8.1 — Installer HMR 2.0
```
pip install git+https://github.com/shubham-goel/4D-Humans
```
- Télécharger les checkpoints du modèle (voir le README du repo)
- Tester en standalone sur une photo de test :
  ```python
  from hmr2.models import HMR2
  model = HMR2.from_pretrained()
  result = model.predict("photo_test.jpg")
  betas = result.smpl_betas  # les 10 paramètres de forme
  ```
- Vérifier que les betas générées produisent un avatar réaliste via smpl_service

### Étape 8.2 — Service backend photo → avatar
- Créer `backend/services/hmr_service.py` :
  - Fonction `extract_betas_from_photo(image_path: str) -> list[float]`
  - Charger le modèle HMR 2.0 (en singleton pour ne pas le recharger à chaque requête)
  - Retourner les 10 betas SMPL
- Créer la route `POST /avatar/from-photo` dans `avatar_router.py` :
  - Recevoir une image en multipart upload
  - Sauvegarder temporairement l'image
  - Appeler `hmr_service.extract_betas_from_photo()`
  - Appeler `smpl_service.generate_avatar_mesh(betas)` pour générer le GLB
  - Retourner `{ betas, glb_url }`

### Étape 8.3 — Interface upload photo frontend
- Créer `frontend/components/PhotoUpload.tsx` :
  - Zone de drag & drop ou bouton "Choisir une photo"
  - Preview de la photo sélectionnée
  - Bouton "Analyser ma morphologie"
  - Loader pendant l'analyse ("Analyse en cours...")
  - Quand les betas reviennent : pré-remplir les sliders + afficher l'avatar 3D
  - L'utilisateur peut ensuite ajuster les sliders manuellement si le résultat n'est pas parfait
- Intégrer ce composant dans la page `/avatar` comme option alternative aux sliders

### Étape 8.4 — Fallback et gestion d'erreurs photo
- Si HMR 2.0 ne détecte pas de personne dans l'image → message d'erreur + proposer les sliders manuels
- Si la photo est trop sombre / floue → message d'avertissement
- Limiter la taille de l'upload (max 10 Mo)
- Accepter uniquement JPG et PNG

**Livrable de la semaine 10 :** L'utilisateur peut uploader une photo et obtenir automatiquement un avatar 3D correspondant à sa morphologie.

---

## Phase 9 — Polissage UI/UX (Semaine 11)

### Étape 9.1 — Animations et transitions
- Animation de chargement personnalisée pour la scène 3D (skeleton loader ou spinner 3D)
- Transitions entre les pages (fade ou slide)
- Animation d'apparition des cartes produit dans le catalogue (stagger)
- Feedback visuel quand les sliders bougent (valeur affichée)

### Étape 9.2 — Enrichir le catalogue
- Passer de 5 à 10–15 produits
- Ajouter des catégories : Hauts, Bas, Robes, Vestes
- Ajouter des filtres fonctionnels dans la page catalogue
- Ajouter un système de recherche basique (par nom)

### Étape 9.3 — Améliorer l'expérience d'essayage
- Afficher le nom du vêtement et la taille recommandée à côté de la scène 3D
- Ajouter des boutons pour changer de couleur (si applicable)
- Ajouter un bouton "Essayer un autre vêtement" sans revenir au catalogue
- Sélecteur de morphotype visible (pour montrer la différence entre les simulations)

### Étape 9.4 — Page d'accueil impactante
- Section hero avec une image/vidéo d'aperçu de la plateforme
- Explication en 3 étapes : "Créez votre avatar → Parcourez le catalogue → Essayez en 3D"
- Bouton d'appel à l'action vers le catalogue ou l'inscription
- Section "Comment ça marche" avec des illustrations

**Livrable de la semaine 11 :** Interface polie, professionnelle, agréable à utiliser.

---

## Phase 10 — Finalisation et préparation de la démo (Semaine 12)

### Étape 10.1 — Tests sur différentes morphologies
- Tester avec au moins 5 profils utilisateurs différents (différents betas)
- Vérifier que le matching morphotype fonctionne correctement
- Vérifier que les GLB se chargent sans erreur pour tous les cas
- Tester sur différents navigateurs (Chrome, Firefox, Safari)

### Étape 10.2 — Documentation technique
- Écrire un `README.md` complet à la racine :
  - Description du projet
  - Instructions d'installation
  - Comment lancer le projet (`npm run dev` + `uvicorn`)
  - Architecture technique (schéma)
  - Technologies utilisées avec justification
- Documenter les routes API (Swagger auto de FastAPI suffit)
- Commenter les fichiers clés du code

### Étape 10.3 — Préparer le script de démonstration
- Écrire un scénario de démo en 5 minutes :
  1. Montrer la page d'accueil et expliquer le concept
  2. Créer un compte en live
  3. Créer un avatar avec les sliders (ou la photo)
  4. Parcourir le catalogue
  5. Essayer 2–3 vêtements en 3D
  6. Montrer la rotation/zoom sur la scène 3D
- Préparer des données de secours (un compte pré-créé, des GLB déjà en cache)
- Tester la démo 3 fois avant la soutenance pour anticiper les problèmes

### Étape 10.4 — Préparer le support de soutenance
- Slides avec : problématique, état de l'art, architecture, démo, résultats, limites, perspectives
- Captures d'écran de l'interface en cas de problème technique pendant la démo
- Schéma d'architecture clair montrant frontend ↔ backend ↔ Blender ↔ SMPL

---

## Checklist récapitulative

| # | Tâche | Phase | Semaine |
|---|-------|-------|---------|
| 1 | Environnement de dev installé | 0 | Pré |
| 2 | Backend FastAPI + auth JWT | 1 | S1 |
| 3 | BDD SQLite avec modèles | 1 | S1 |
| 4 | Service SMPL → GLB | 2 | S2 |
| 5 | Route POST /avatar/create | 2 | S2 |
| 6 | Frontend Next.js initialisé | 3 | S3 |
| 7 | Page auth (inscription/connexion) | 3 | S3 |
| 8 | Composant AvatarScene.tsx (R3F) | 3 | S3 |
| 9 | Page avatar avec sliders | 3 | S3 |
| 10 | Catalogue JSON + routes API | 4 | S4 |
| 11 | Page catalogue + fiches produit | 4 | S4 |
| 12 | Navigation + layout global | 4 | S4 |
| 13 | 3 vêtements modélisés dans Blender | 5 | S5 |
| 14 | Script simulation Blender headless | 5 | S5–6 |
| 15 | Pré-simulation sur 3–5 morphotypes | 5 | S6 |
| 16 | Compression Draco des GLB | 5 | S6 |
| 17 | Logique matching morphotype | 6 | S7 |
| 18 | Route POST /tryon/request | 6 | S7 |
| 19 | Page d'essayage 3D complète | 6 | S7 |
| 20 | Test parcours end-to-end | 7 | S8 |
| 21 | Gestion d'erreurs | 7 | S8 |
| 22 | Responsive | 7 | S8 |
| 23 | Installation HMR 2.0 | 8 | S9 |
| 24 | Route POST /avatar/from-photo | 8 | S9–10 |
| 25 | Upload photo frontend | 8 | S10 |
| 26 | Polissage UI/UX | 9 | S11 |
| 27 | 10–15 produits au catalogue | 9 | S11 |
| 28 | Tests multi-morphologies | 10 | S12 |
| 29 | README + documentation | 10 | S12 |
| 30 | Script de démo + soutenance | 10 | S12 |

---

## Conseil stratégique important

**Travaille d'abord avec un GLB statique.** Avant de connecter toute la pipeline automatique (SMPL → Blender → GLB), fais fonctionner la scène 3D avec un fichier GLB créé à la main dans Blender. L'objectif est de valider l'expérience utilisateur (navigation 3D, chargement, interface) avant de passer du temps sur l'automatisation. Si la démo 3D marche avec un fichier statique, tu as déjà 80% de l'impact visuel du projet.
