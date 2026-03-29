# ADR 001 — Blender comme moteur 3D plutôt que Unity/Unreal

**Date** : 2026-03-29
**Statut** : Accepted
**Auteur** : Axel SAMVELYAN

## Contexte

WEARME nécessite un moteur capable de :
1. Simuler le comportement physique des tissus (cloth simulation)
2. Manipuler des meshes paramétriques complexes (SMPL)
3. Être scriptable en Python (pour l'intégration avec `wearme`)
4. Exporter en formats standards (GLB, OBJ)
5. Fonctionner localement sans licence commerciale coûteuse

## Décision

Nous utilisons **Blender 4.x** comme moteur 3D et simulateur tissu.

## Alternatives considérées

### Unity
- ✅ Large écosystème, bonne documentation
- ✅ Cloth simulation via Unity Cloth
- ❌ Scripting Python limité (C# natif)
- ❌ Licence commerciale requise au-delà d'un certain seuil de revenus
- ❌ Pas de pipeline CLI simple pour l'automatisation
- ❌ Overhead important pour une app locale sans temps réel requis

### Unreal Engine
- ✅ Rendu photoréaliste
- ✅ Cloth simulation avancée (Chaos Cloth)
- ❌ Très lourd pour un MVP local
- ❌ Scripting Python expérimental
- ❌ Courbe d'apprentissage élevée
- ❌ Pas adapté à un usage headless/scripté

### Three.js / Babylon.js (web)
- ✅ Déploiement web facile
- ❌ Simulation tissu côté client très limitée
- ❌ Hors périmètre MVP (pipeline web-first exclu)

### Solution custom (Trimesh + PyBullet/Taichi)
- ✅ Contrôle total
- ❌ Simulation tissu réaliste extrêmement complexe à implémenter
- ❌ Des mois de travail pour un résultat inférieur à Blender Cloth

## Justification du choix Blender

1. **Python natif** : Blender expose son API complète via `bpy` — intégration directe avec `wearme`
2. **Cloth simulation production-ready** : Blender Cloth couvre 100% des besoins MVP
3. **Open source & gratuit** : aucune contrainte de licence
4. **Export GLB/OBJ natif** : formats ciblés supportés out-of-the-box
5. **Headless/CLI** : `blender --background --python script.py` permet l'automatisation
6. **Communauté active** : documentation et exemples abondants pour le scripting

## Conséquences

- Les scripts Blender injectent le package `wearme` via `sys.path` (pas de `bpy` pip)
- La simulation ne tourne pas dans le processus Python principal — appel subprocess
- Tests unitaires de `wearme.sim` nécessitent une installation Blender (marqués `pytest.mark.blender`)
- Le rendu est baked (non temps-réel) — acceptable pour le périmètre MVP
