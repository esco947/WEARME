"""
Service de détection de pose MediaPipe — CPU natif, aucun WebGL requis.
Utilisé par POST /pose/detect pour remplacer le WASM côté navigateur.
"""

import os
import base64
import urllib.request
import numpy as np
from PIL import Image, ImageOps
import io

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"
)
MODEL_PATH = os.path.realpath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'models', 'pose_landmarker_full.task'
))

_landmarker: mp_vision.PoseLandmarker | None = None


def _get_landmarker() -> mp_vision.PoseLandmarker:
    global _landmarker
    if _landmarker is not None:
        return _landmarker

    if not os.path.exists(MODEL_PATH):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print(f"[pose_service] Téléchargement du modèle depuis {MODEL_URL} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"[pose_service] Modèle sauvegardé : {MODEL_PATH}")

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.IMAGE,
        num_poses=1,
        output_segmentation_masks=True,
    )
    _landmarker = mp_vision.PoseLandmarker.create_from_options(options)
    print("[pose_service] PoseLandmarker CPU prêt.")
    return _landmarker


def detect_pose_from_bytes(image_bytes: bytes) -> dict:
    """
    Détecte la pose dans une image.
    - Corrige l'orientation EXIF via Pillow (ImageOps.exif_transpose)
    - Redimensionne à max 1024 px pour la vitesse
    - Retourne landmarks + masque de segmentation float32 encodé base64
    """
    landmarker = _get_landmarker()

    pil_img = Image.open(io.BytesIO(image_bytes))
    pil_img = ImageOps.exif_transpose(pil_img)  # équivalent normalizeImageOrientation
    pil_img = pil_img.convert('RGB')

    # Redimensionner à max 1024 px (côté le plus long)
    w, h = pil_img.size
    if max(w, h) > 1024:
        scale = 1024 / max(w, h)
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    img_np = np.array(pil_img, dtype=np.uint8)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)

    result = landmarker.detect(mp_image)

    if not result.pose_landmarks:
        return {
            "landmarks": [],
            "world_landmarks": [],
            "segmentation_mask_b64": None,
            "mask_width": 0,
            "mask_height": 0,
        }

    landmarks = [
        {"x": float(lm.x), "y": float(lm.y), "z": float(lm.z),
         "visibility": float(lm.visibility or 0.0)}
        for lm in result.pose_landmarks[0]
    ]

    world_landmarks = [
        {"x": float(lm.x), "y": float(lm.y), "z": float(lm.z),
         "visibility": float(lm.visibility or 0.0)}
        for lm in (result.pose_world_landmarks[0]
                   if result.pose_world_landmarks
                   else result.pose_landmarks[0])
    ]

    mask_b64 = None
    mask_w = mask_h = 0
    if result.segmentation_masks:
        mask_np = result.segmentation_masks[0].numpy_view()
        if mask_np.ndim == 3:
            mask_np = mask_np[:, :, 0]
        mask_h, mask_w = int(mask_np.shape[0]), int(mask_np.shape[1])
        flat = np.ascontiguousarray(mask_np, dtype=np.float32).flatten()
        mask_b64 = base64.b64encode(flat.tobytes()).decode('utf-8')

    return {
        "landmarks": landmarks,
        "world_landmarks": world_landmarks,
        "segmentation_mask_b64": mask_b64,
        "mask_width": mask_w,
        "mask_height": mask_h,
    }
