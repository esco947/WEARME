import json
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/products", tags=["catalogue"])

CATALOGUE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "catalogue.json"
)

# Chargement en mémoire au démarrage
with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
    _products: list[dict] = json.load(f)

_products_by_id: dict[str, dict] = {p["id"]: p for p in _products}


@router.get("")
def get_products(
    type: Optional[str] = Query(None, description="Filtrer par type (top, bottom, dress, jacket)"),
    brand: Optional[str] = Query(None, description="Filtrer par marque"),
):
    results = _products
    if type:
        results = [p for p in results if p.get("type") == type]
    if brand:
        results = [p for p in results if p.get("brand", "").lower() == brand.lower()]
    return results


@router.get("/{product_id}")
def get_product(product_id: str):
    product = _products_by_id.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product
