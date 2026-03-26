from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import engine
import models
from routers import auth_router, avatar_router, catalogue_router, pose_router

# Créer les tables en BDD au démarrage
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FitView API", version="1.0.0")

# CORS — autoriser le frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers statiques (GLB avatars, simulations, images)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Routers
app.include_router(auth_router.router)
app.include_router(avatar_router.router)
app.include_router(catalogue_router.router)
app.include_router(pose_router.router)


@app.get("/")
def root():
    return {"status": "ok", "app": "FitView API"}
