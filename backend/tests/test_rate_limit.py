from fastapi.testclient import TestClient


def test_requests_are_rate_limited(tmp_path, monkeypatch):
    monkeypatch.setenv("XQ_DB", str(tmp_path / "rate.db"))
    monkeypatch.setenv("XQ_RATE_LIMIT", "2")

    from app.main import create_app

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/scenes").status_code == 200
        assert client.get("/api/v1/scenes").status_code == 200
        assert client.get("/api/v1/scenes").status_code == 429


def test_health_is_not_rate_limited(tmp_path, monkeypatch):
    monkeypatch.setenv("XQ_DB", str(tmp_path / "rate2.db"))
    monkeypatch.setenv("XQ_RATE_LIMIT", "1")

    from app.main import create_app

    with TestClient(create_app()) as client:
        for _ in range(5):
            assert client.get("/health").status_code == 200