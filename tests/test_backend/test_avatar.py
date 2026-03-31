"""Tests for avatar endpoints: GET/PUT params, measurements (mocked)."""

from __future__ import annotations

from unittest.mock import patch


class TestGetAvatar:
    def test_get_avatar(self, client, auth_headers):
        resp = client.get("/api/avatar", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["gender"] == "neutral"
        assert data["height_m"] == 1.75
        assert data["weight_kg"] == 70.0
        assert data["betas"] == [0.0] * 10

    def test_get_avatar_unauthenticated(self, client):
        resp = client.get("/api/avatar")
        assert resp.status_code == 401


class TestUpdateAvatar:
    def test_update_gender(self, client, auth_headers):
        resp = client.put("/api/avatar", json={"gender": "female"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["gender"] == "female"

    def test_update_height(self, client, auth_headers):
        resp = client.put("/api/avatar", json={"height_m": 1.80}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["height_m"] == 1.80

    def test_update_betas(self, client, auth_headers):
        new_betas = [1.0, -1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        resp = client.put("/api/avatar", json={"betas": new_betas}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["betas"] == new_betas

    def test_update_partial(self, client, auth_headers):
        """Only supplied fields are updated."""
        client.put("/api/avatar", json={"height_m": 1.90}, headers=auth_headers)
        resp = client.get("/api/avatar", headers=auth_headers)
        data = resp.json()
        assert data["height_m"] == 1.90
        assert data["gender"] == "neutral"  # unchanged

    def test_update_invalid_gender(self, client, auth_headers):
        resp = client.put("/api/avatar", json={"gender": "alien"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_update_height_out_of_range(self, client, auth_headers):
        resp = client.put("/api/avatar", json={"height_m": 3.0}, headers=auth_headers)
        assert resp.status_code == 422

    def test_update_betas_wrong_length(self, client, auth_headers):
        resp = client.put("/api/avatar", json={"betas": [0.0] * 5}, headers=auth_headers)
        assert resp.status_code == 422


class TestMeasurements:
    def test_measurements_mocked(self, client, auth_headers):
        mock_result = {
            "height_m": 1.72,
            "chest_m": 0.95,
            "waist_m": 0.80,
            "hips_m": 0.98,
        }
        with patch("backend.services.avatar_service.get_measurements", return_value=mock_result):
            resp = client.get("/api/avatar/measurements", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["height_m"] == 1.72
        assert data["chest_m"] == 0.95
        assert data["waist_m"] == 0.80
        assert data["hips_m"] == 0.98

    def test_measurements_unauthenticated(self, client):
        resp = client.get("/api/avatar/measurements")
        assert resp.status_code == 401


class TestMesh:
    def test_mesh_mocked(self, client, auth_headers):
        fake_glb = b"glTF\x02\x00\x00\x00"  # minimal fake GLB header
        with patch("backend.services.avatar_service.get_glb_bytes", return_value=fake_glb):
            resp = client.get("/api/avatar/mesh", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "model/gltf-binary"
        assert resp.content == fake_glb

    def test_mesh_unauthenticated(self, client):
        resp = client.get("/api/avatar/mesh")
        assert resp.status_code == 401
