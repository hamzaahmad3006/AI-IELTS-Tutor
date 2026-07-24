"""Smoke test: admin user management (list, suspend, role change) + RBAC."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_admin_users.db")

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402


def run() -> None:
    settings = get_settings()
    with TestClient(app) as client:
        # A learner
        client.post(
            "/v1/auth/register",
            json={"fullName": "Learner One", "email": "learner1@example.com", "password": "StrongPass123"},
        )
        learner = client.post(
            "/v1/auth/login",
            json={"email": "learner1@example.com", "password": "StrongPass123"},
        ).json()
        lh = {"Authorization": f"Bearer {learner['tokens']['accessToken']}"}
        learner_id = learner["user"]["id"]

        # Learner cannot access admin user management
        assert client.get("/v1/admin/users", headers=lh).status_code == 403

        # Seeded admin
        admin = client.post(
            "/v1/auth/login",
            json={"email": settings.seed_admin_email, "password": settings.seed_admin_password},
        ).json()
        ah = {"Authorization": f"Bearer {admin['tokens']['accessToken']}"}
        admin_id = admin["user"]["id"]

        # List users (admin + learner exist) and paginate
        r = client.get("/v1/admin/users?limit=1", headers=ah)
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) == 1
        assert r.json()["nextCursor"] is not None

        # Search finds the learner
        r = client.get("/v1/admin/users?search=learner1", headers=ah)
        assert r.status_code == 200, r.text
        assert any(u["email"] == "learner1@example.com" for u in r.json()["items"])

        # Suspend the learner
        r = client.patch(f"/v1/admin/users/{learner_id}", headers=ah, json={"isActive": False})
        assert r.status_code == 200, r.text
        assert r.json()["isActive"] is False

        # Suspended learner can no longer log in
        r = client.post(
            "/v1/auth/login",
            json={"email": "learner1@example.com", "password": "StrongPass123"},
        )
        assert r.status_code == 403, r.text

        # Admin may assign a non-privileged role
        r = client.patch(f"/v1/admin/users/{learner_id}", headers=ah, json={"role": "content_editor"})
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "content_editor"

        # A plain admin may NOT grant a privileged role (super_admin only)
        r = client.patch(f"/v1/admin/users/{learner_id}", headers=ah, json={"role": "admin"})
        assert r.status_code == 403, r.text

        # Admin cannot suspend their own account
        r = client.patch(f"/v1/admin/users/{admin_id}", headers=ah, json={"isActive": False})
        assert r.status_code == 400, r.text

    print("ADMIN USERS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
