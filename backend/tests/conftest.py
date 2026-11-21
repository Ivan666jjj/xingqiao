import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ADMIN = {"X-Admin-Token": "test-admin"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("XQ_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("XQ_ADMIN_TOKEN", "test-admin")
    monkeypatch.setenv("XQ_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("XQ_RATE_LIMIT", "10000")

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def enroll(client, code="P-001", age_band="12-14"):
    r = client.post(
        "/api/v1/participants",
        json={
            "code": code,
            "ageBand": age_band,
            "gender": "unspecified",
            "diagnosisStatus": "diagnosed",
            "languageLevel": "verbal",
        },
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text
    return r.json()


def give_consent(client, token):
    r = client.post(
        "/api/v1/consent",
        json={
            "version": "2026-11-21",
            "scopes": ["practice"],
            "guardianConfirmed": True,
            "childAssent": True,
            "method": "digital",
            "guardianRef": "guardian-demo-001",
        },
        headers=auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def start(client, token, scene="borrow"):
    return client.post(
        "/api/v1/sessions",
        json={"sceneId": scene, "mode": "solo"},
        headers=auth(token),
    )