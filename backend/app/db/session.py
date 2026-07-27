from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine, enabling FK enforcement for SQLite.

    SQLite disables foreign-key enforcement per-connection by default, so
    ON DELETE CASCADE/RESTRICT is otherwise a silent no-op.
    """
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    new_engine = create_engine(database_url, connect_args=connect_args)
    if is_sqlite:
        event.listen(new_engine, "connect", _enable_sqlite_foreign_keys)
    return new_engine


engine = build_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
