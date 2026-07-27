from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_url(tmp_path) -> str:
    db_path = tmp_path / "test.db"
    return f"sqlite:///{db_path}"


@pytest.fixture()
def client(db_url, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from app.core.config import get_settings
    from app.db import session as db_session

    get_settings.cache_clear()

    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(db_session, "SessionLocal", test_session_local)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
