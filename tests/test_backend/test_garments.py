"""Tests for garment catalogue endpoints."""

from __future__ import annotations

import json

from backend.database import get_db
from backend.models import Garment


def _seed_garments(client):
    """Insert test garments via the overridden DB dependency."""
    db = next(client.app.dependency_overrides[get_db]())
    try:
        garments = [
            Garment(
                id="g-001",
                name="T-Shirt Test",
                category="t-shirt",
                description="A test t-shirt.",
                sizes=json.dumps(["S", "M", "L"]),
            ),
            Garment(
                id="g-002",
                name="Hoodie Test",
                category="hoodie",
                description="A test hoodie.",
                sizes=json.dumps(["M", "L", "XL"]),
            ),
        ]
        db.add_all(garments)
        db.commit()
    finally:
        db.close()


class TestListGarments:
    def test_list_empty(self, client):
        resp = client.get("/api/garments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_garments(self, client):
        _seed_garments(client)
        resp = client.get("/api/garments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {g["name"] for g in data["items"]}
        assert "T-Shirt Test" in names
        assert "Hoodie Test" in names

    def test_list_no_auth_required(self, client):
        """Garment list is public."""
        resp = client.get("/api/garments")
        assert resp.status_code == 200


class TestGetGarment:
    def test_get_existing(self, client):
        _seed_garments(client)
        resp = client.get("/api/garments/g-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "g-001"
        assert data["name"] == "T-Shirt Test"
        assert data["sizes"] == ["S", "M", "L"]

    def test_get_not_found(self, client):
        resp = client.get("/api/garments/nonexistent")
        assert resp.status_code == 404

    def test_get_no_auth_required(self, client):
        """Garment detail is public."""
        _seed_garments(client)
        resp = client.get("/api/garments/g-001")
        assert resp.status_code == 200
