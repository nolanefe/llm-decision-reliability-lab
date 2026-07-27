from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_expected_body(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_app_starts_without_openai_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'startup.db'}")

    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        from app.main import app

        settings = get_settings()
        assert settings.openai_api_key is None
        assert app is not None
    finally:
        get_settings.cache_clear()
