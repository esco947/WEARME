"""Tests for avatar endpoints: GET/PUT gender, sliders, measurements, mesh."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import numpy as np


class TestGetAvatar:
    def test_get_avatar(self, client, auth_headers):
        resp = client.get("/api/avatar", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["gender"] in ("male", "female")
        assert data["betas"] == [0.0] * 10
        assert isinstance(data["measurements"], dict)

    def test_get_avatar_unauthenticated(self, client):
        resp = client.get("/api/avatar")
        assert resp.status_code == 401


class TestUpdateGender:
    def test_update_gender_male(self, client, auth_headers):
        resp = client.put("/api/avatar/gender", json={"gender": "male"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["gender"] == "male"

    def test_update_gender_female(self, client, auth_headers):
        resp = client.put("/api/avatar/gender", json={"gender": "female"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["gender"] == "female"

    def test_update_invalid_gender(self, client, auth_headers):
        resp = client.put("/api/avatar/gender", json={"gender": "alien"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_gender_resets_betas(self, client, auth_headers):
        """Changing gender resets betas to zeros."""
        resp = client.put("/api/avatar/gender", json={"gender": "female"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["betas"] == [0.0] * 10

    def test_update_gender_unauthenticated(self, client):
        resp = client.put("/api/avatar/gender", json={"gender": "male"})
        assert resp.status_code == 401


class TestUpdateSliders:
    def _mock_service(self):
        """Return a mock avatar response dict."""
        return {
            "id": "test-id",
            "gender": "male",
            "betas": [0.1] * 10,
            "measurements": {
                "height": 1.80,
                "chest_circumference": 0.99,
                "waist_circumference": 0.84,
                "hip_circumference": 0.97,
                "shoulder_width": 0.45,
                "inseam": 0.81,
            },
        }

    def test_update_sliders_valid(self, client, auth_headers):
        targets = {"height": 1.80, "chest_circumference": 0.99}
        with patch(
            "backend.services.avatar_service.update_from_sliders",
            return_value={"height": 1.80, "chest_circumference": 0.99},
        ):
            resp = client.put("/api/avatar/sliders", json={"targets": targets}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "betas" in data
        assert "measurements" in data

    def test_update_sliders_unauthenticated(self, client):
        resp = client.put("/api/avatar/sliders", json={"targets": {"height": 1.75}})
        assert resp.status_code == 401


class TestMeasurements:
    def test_measurements_endpoint(self, client, auth_headers):
        resp = client.get("/api/avatar/measurements", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "measurements" in data
        assert isinstance(data["measurements"], dict)

    def test_measurements_unauthenticated(self, client):
        resp = client.get("/api/avatar/measurements")
        assert resp.status_code == 401


class TestMesh:
    def test_mesh_returns_glb(self, client, auth_headers):
        fake_glb = b"glTF\x02\x00\x00\x00" + b"\x00" * 20
        with patch(
            "backend.services.avatar_service.get_glb",
            return_value=fake_glb,
        ):
            resp = client.get("/api/avatar/mesh", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "model/gltf-binary"

    def test_mesh_unauthenticated(self, client):
        resp = client.get("/api/avatar/mesh")
        assert resp.status_code == 401
