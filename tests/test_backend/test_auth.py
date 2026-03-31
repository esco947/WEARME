"""Tests for auth endpoints: register, login, /me."""

from __future__ import annotations


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@test.com", "password": "password123"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "new@test.com"
        assert "id" in data["user"]

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@test.com", "password": "password123"}
        client.post("/api/auth/register", json=payload)
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "short@test.com", "password": "abc"},
        )
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert resp.status_code == 422

    def test_register_creates_default_avatar(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "avatar@test.com", "password": "password123"},
        )
        token = resp.json()["access_token"]
        avatar_resp = client.get("/api/avatar", headers={"Authorization": f"Bearer {token}"})
        assert avatar_resp.status_code == 200
        avatar = avatar_resp.json()
        assert avatar["gender"] == "neutral"
        assert len(avatar["betas"]) == 10
        assert avatar["height_m"] == 1.75
        assert avatar["weight_kg"] == 70.0


class TestLogin:
    def test_login_success(self, client):
        client.post("/api/auth/register", json={"email": "login@test.com", "password": "password123"})
        resp = client.post("/api/auth/login", json={"email": "login@test.com", "password": "password123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@test.com"

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={"email": "wp@test.com", "password": "password123"})
        resp = client.post("/api/auth/login", json={"email": "wp@test.com", "password": "wrongpassword"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/api/auth/login", json={"email": "unknown@test.com", "password": "password123"})
        assert resp.status_code == 401


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        resp = client.get("/api/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/api/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
