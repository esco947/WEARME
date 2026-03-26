"""
Service de génération d'avatar SMPL.
Charge le modèle PKL (male/female/neutral) et applique les betas pour générer un GLB personnalisé.
"""

import os
import pickle
import warnings
import numpy as np

warnings.filterwarnings("ignore")

_BASE = os.path.realpath(os.path.dirname(__file__))
_MODELS_DIR = os.path.realpath(os.path.join(
    _BASE, "..", "..", "data", "smpl_model",
    "SMPL_python_v.1.1.0", "smpl", "models"
))
_STATIC_DIR = os.path.realpath(os.path.join(_BASE, "..", "..", "static"))

_PKL_FILES = {
    "male":    "basicmodel_m_lbs_10_207_0_v1.1.0.pkl",
    "female":  "basicmodel_f_lbs_10_207_0_v1.1.0.pkl",
    "neutral": "basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl",
}

_model_cache: dict = {}


class _CompatUnpickler(pickle.Unpickler):
    def __init__(self, f):
        super().__init__(f, encoding="latin1")

    def find_class(self, module, name):
        if module == "scipy.sparse.csc":
            import scipy.sparse
            return scipy.sparse.csc_matrix
        if module.startswith("chumpy"):
            class _Stub:
                def __setstate__(self, s):
                    if isinstance(s, dict):
                        self.__dict__.update(s)
            return _Stub
        return super().find_class(module, name)


def _load_model(gender: str) -> dict:
    if gender not in _PKL_FILES:
        gender = "neutral"
    if gender in _model_cache:
        return _model_cache[gender]

    pkl_path = os.path.join(_MODELS_DIR, _PKL_FILES[gender])
    if not os.path.exists(pkl_path):
        raise FileNotFoundError(f"Modèle SMPL introuvable : {pkl_path}")

    print(f"[smpl_service] Chargement du modèle {gender} depuis {pkl_path}")
    with open(pkl_path, "rb") as f:
        dd = _CompatUnpickler(f).load()

    v_template = np.array(dd["v_template"], dtype=np.float32)   # (6890, 3)
    shapedirs  = np.array(dd["shapedirs"].x, dtype=np.float32)  # (6890, 3, 300)
    faces      = np.array(dd["f"], dtype=np.uint32)              # (13776, 3)

    _model_cache[gender] = {
        "v_template": v_template,
        "shapedirs":  shapedirs,
        "faces":      faces,
    }
    print(f"[smpl_service] Modèle {gender} chargé. v_template={v_template.shape}, shapedirs={shapedirs.shape}")
    return _model_cache[gender]


def generate_avatar_glb(betas: list[float], output_path: str, gender: str = "neutral") -> str:
    """
    Génère un GLB d'avatar SMPL à partir des betas et du genre.

    Args:
        betas: 10 floats représentant la forme corporelle SMPL.
        output_path: Chemin absolu de sortie du GLB.
        gender: "male", "female" ou "neutral".

    Returns:
        Chemin relatif depuis /static/ du fichier GLB généré.

    Raises:
        Exception si la génération ou l'export échoue.
    """
    import trimesh

    output_path = os.path.realpath(output_path)
    print(f"[smpl_service] Génération avatar {gender} -> {output_path}")

    model = _load_model(gender)
    betas_arr = np.array(betas, dtype=np.float32)
    n = len(betas_arr)  # utilise exactement le nombre de betas fournis

    # Appliquer les shape blend shapes
    # v_shaped[i,j] = v_template[i,j] + Σ_k shapedirs[i,j,k] * betas[k]
    v_shaped = model["v_template"] + np.einsum(
        "ijk,k->ij", model["shapedirs"][:, :, :n], betas_arr
    )  # (6890, 3) float32

    # Positionner les pieds à y=0
    v_shaped[:, 1] -= v_shaped[:, 1].min()

    # Créer le dossier de sortie
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Créer le mesh avec calcul des normales (process=True)
    mesh = trimesh.Trimesh(
        vertices=v_shaped,
        faces=model["faces"],
        process=True,    # calcule les normales -> meilleur rendu
    )

    # Export explicite en GLB (pas de déduction par extension)
    glb_bytes = mesh.export(file_type="glb")
    if not glb_bytes:
        raise RuntimeError("trimesh.export a retourné un résultat vide")

    with open(output_path, "wb") as f:
        f.write(glb_bytes)

    size = os.path.getsize(output_path)
    if size == 0:
        raise RuntimeError(f"GLB écrit à {output_path} mais fichier vide (0 bytes)")

    print(f"[smpl_service] GLB généré avec succès : {output_path} ({size} bytes)")

    # Retourner le chemin relatif depuis /static/
    rel = os.path.relpath(output_path, _STATIC_DIR).replace("\\", "/")
    return rel
