# WEARME — Git workflow

## Branches

| Branche | Rôle |
|---------|------|
| `main` | Stable uniquement — jamais de commit direct après l'initialisation |
| `dev` | Intégration — merge depuis `feature/*` et `fix/*` |
| `feature/<nom>` | Une feature = une branche |
| `fix/<nom>` | Correction de bug |
| `chore/<nom>` | Maintenance, refactor |

## Flux standard

```
main
 └─ dev
     └─ feature/body-manual
               │
               └─ (PR) ──→ dev ──→ (PR release) ──→ main
```

## Conventions de commit — Conventional Commits

```
<type>(<scope>): <description courte>
```

### Types autorisés

| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `test` | Ajout/modification de tests |
| `docs` | Documentation |
| `chore` | Maintenance, config, CI |
| `refactor` | Restructuration sans changement fonctionnel |
| `style` | Formatage, linting (pas de changement logique) |

### Règles

- **1 commit = 1 changement logique**
- Jamais de commit qui casse les tests existants
- Jamais de commit de plus de 300 lignes changées
- Jamais de message `WIP`, `fix stuff`, `update`
- Message en **anglais**, **impératif**, **minuscule** après le type
- Jamais de merge `feature →  main` directement (passer par `dev`)

### Exemples

```
feat(body): add BodyParameters dataclass with validation
fix(io): handle missing parent directory in save_json
test(body): add round-trip serialisation tests for BodyParameters
docs: update roadmap with Phase 1 status
chore: update ruff config to ignore E501
refactor(core): extract unit conversion helpers to units.py
```

## Scopes courants

| Scope | Module concerné |
|-------|-----------------|
| `core` | `wearme.core.*` |
| `body` | `wearme.body.*` |
| `vision` | `wearme.vision.*` |
| `garments` | `wearme.garments.*` |
| `sim` | `wearme.sim.*` |
| `io` | `wearme.io.*` |
| `blender` | `blender_addon/` |
| `scripts` | `scripts/` |
| `tests` | `tests/` |
| `deps` | `requirements/`, `pyproject.toml` |
