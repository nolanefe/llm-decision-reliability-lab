from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "dataset_items",
    "prompt_versions",
    "experiments",
    "runs",
    "evaluations",
}


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _use_temp_database(tmp_path, monkeypatch, name: str) -> str:
    from app.core.config import get_settings

    database_url = f"sqlite:///{tmp_path / name}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    return database_url


def test_upgrade_head_creates_all_expected_tables(tmp_path, monkeypatch) -> None:
    from app.core.config import get_settings

    database_url = _use_temp_database(tmp_path, monkeypatch, "migration_upgrade.db")
    try:
        command.upgrade(_alembic_config(), "head")

        engine = create_engine(database_url)
        tables = set(inspect(engine).get_table_names())
        engine.dispose()

        assert EXPECTED_TABLES.issubset(tables)
    finally:
        get_settings.cache_clear()


def test_downgrade_base_drops_all_expected_tables(tmp_path, monkeypatch) -> None:
    from app.core.config import get_settings

    database_url = _use_temp_database(tmp_path, monkeypatch, "migration_downgrade.db")
    try:
        config = _alembic_config()
        command.upgrade(config, "head")
        command.downgrade(config, "base")

        engine = create_engine(database_url)
        tables = set(inspect(engine).get_table_names())
        engine.dispose()

        assert not EXPECTED_TABLES.intersection(tables)
    finally:
        get_settings.cache_clear()
