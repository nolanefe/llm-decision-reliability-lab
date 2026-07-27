from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def db_url(tmp_path) -> str:
    db_path = tmp_path / "test.db"
    return f"sqlite:///{db_path}"


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    from app import models  # noqa: F401
    from app.db.base import Base
    from app.db.session import build_engine

    db_path = tmp_path / "models_test.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_url, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from app.core.config import get_settings
    from app.db import session as db_session
    from app.db.session import build_engine

    get_settings.cache_clear()

    test_engine = build_engine(db_url)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(db_session, "SessionLocal", test_session_local)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
