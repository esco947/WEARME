from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models
from services.pose_service import detect_pose_from_bytes

router = APIRouter(prefix="/pose", tags=["pose"])


@router.post("/detect")
async def detect_pose(
    front: UploadFile = File(...),
    profile: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Détecte la pose dans deux images (face + profil).
    Retourne les landmarks et masques de segmentation en JSON.
    Traitement CPU pur — aucun WebGL requis côté serveur.
    """
    try:
        front_bytes = await front.read()
        profile_bytes = await profile.read()

        front_result = detect_pose_from_bytes(front_bytes)
        profile_result = detect_pose_from_bytes(profile_bytes)

        return {"front": front_result, "profile": profile_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur analyse pose : {e}")
