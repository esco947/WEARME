import json
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from services.smpl_service import generate_avatar_glb
import models

router = APIRouter(prefix="/avatar", tags=["avatar"])

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


class AvatarCreateRequest(BaseModel):
    betas: list[float]
    gender: str = "neutral"  # "male", "female" ou "neutral"


class AvatarResponse(BaseModel):
    avatar_id: int
    glb_url: str
    betas: list[float]
    gender: str


@router.post("/create", response_model=AvatarResponse)
def create_avatar(
    body: AvatarCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not (1 <= len(body.betas) <= 20):
        raise HTTPException(status_code=400, detail="Entre 1 et 20 betas requis")
    if body.gender not in ("male", "female", "neutral"):
        raise HTTPException(status_code=400, detail="Genre invalide (male/female/neutral)")

    output_path = os.path.realpath(os.path.join(
        os.path.dirname(__file__), "..", "..", "static",
        "avatars", str(current_user.id), "avatar.glb"
    ))
    print(f"[avatar_router] Génération pour user {current_user.id}, genre={body.gender}, path={output_path}")

    try:
        glb_relative = generate_avatar_glb(body.betas, output_path, body.gender)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération avatar : {e}")

    avatar = models.Avatar(
        user_id=current_user.id,
        betas=json.dumps(body.betas),
        gender=body.gender,
        glb_path=glb_relative,
    )
    db.add(avatar)
    db.commit()
    db.refresh(avatar)

    glb_url = f"{BASE_URL}/static/{glb_relative}" if glb_relative else ""

    return {
        "avatar_id": avatar.id,
        "glb_url": glb_url,
        "betas": body.betas,
        "gender": body.gender,
    }


@router.get("/{avatar_id}", response_model=AvatarResponse)
def get_avatar(
    avatar_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    avatar = db.query(models.Avatar).filter(
        models.Avatar.id == avatar_id,
        models.Avatar.user_id == current_user.id,
    ).first()

    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")

    glb_url = f"{BASE_URL}/static/{avatar.glb_path}" if avatar.glb_path else ""

    return {
        "avatar_id": avatar.id,
        "glb_url": glb_url,
        "betas": json.loads(avatar.betas),
        "gender": avatar.gender or "neutral",
    }
