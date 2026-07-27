import logging

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


class TestDatabaseErrorHandling:
    def test_returns_generic_response_and_logs_details_server_side(
        self, client: TestClient, monkeypatch, caplog
    ) -> None:
        from app.api import experiments as experiments_router

        def _boom(db, payload):
            raise OperationalError(
                "INSERT INTO experiments (...) VALUES (...)",
                {},
                Exception("disk I/O error at /var/secret/reliability_lab.db"),
            )

        monkeypatch.setattr(experiments_router.service, "create_experiment", _boom)

        with caplog.at_level(logging.ERROR):
            response = client.post(
                "/api/v1/experiments",
                json={
                    "name": "x",
                    "dataset_item_ids": [1],
                    "prompt_version_ids": [1],
                    "model_names": ["gpt-4o-mini"],
                    "repeat_count": 1,
                },
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "A database error occurred."}

        # Nothing from the underlying exception leaks into the client response.
        assert "disk I/O error" not in response.text
        assert "/var/secret" not in response.text
        assert "INSERT INTO" not in response.text

        # But it is logged server-side for debugging.
        assert any(
            "Unhandled database error" in record.message for record in caplog.records
        )
