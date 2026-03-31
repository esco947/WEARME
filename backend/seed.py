"""Seed the database with garments from data/catalogue.json.

Usage::

    python backend/seed.py

Idempotent: garments are inserted only if they don't already exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, engine
from backend.models import Base, Garment

CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "data" / "catalogue.json"


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    catalogue = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        inserted = 0
        for item in catalogue:
            if db.get(Garment, item["id"]) is None:
                garment = Garment(
                    id=item["id"],
                    name=item["name"],
                    category=item["category"],
                    description=item.get("description", ""),
                    sizes=json.dumps(item.get("sizes", ["XS", "S", "M", "L", "XL"])),
                    thumbnail_url=item.get("thumbnail_url"),
                )
                db.add(garment)
                inserted += 1
        db.commit()
        print(f"Seeded {inserted} garment(s) (skipped {len(catalogue) - inserted} existing).")


if __name__ == "__main__":
    seed()
