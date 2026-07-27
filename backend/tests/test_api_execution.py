"""API-level execution tests. Every test overrides the LLM provider
dependency with a fake, or never reaches it — none call the real OpenAI API."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.fakes import ScriptedProvider, make_result

VALID_OUTPUT = (
    '{"category": "billing", "priority": "high", "summary": "s", '
    '"recommended_action": "a"}'
)


def _create_dataset_item(client: TestClient, **overrides) -> dict:
    payload = dict(
        name="billing-refund",
        input_text="I was charged twice for my subscription.",
        expected_category="billing",
        expected_priority="high",
    )
    payload.update(overrides)
    return client.post("/api/v1/dataset-items", json=payload).json()


def _create_prompt_version(client: TestClient, **overrides) -> dict:
    payload = dict(
        name="baseline", version=1, template_text="Classify this ticket: {ticket_text}"
    )
    payload.update(overrides)
    return client.post("/api/v1/prompt-versions", json=payload).json()


def _create_experiment(client: TestClient, item_id: int, prompt_id: int, **overrides) -> dict:
    payload = dict(
        name="baseline-comparison",
        dataset_item_ids=[item_id],
        prompt_version_ids=[prompt_id],
        model_names=["gpt-5-mini"],
        repeat_count=1,
    )
    payload.update(overrides)
    return client.post("/api/v1/experiments", json=payload).json()


@pytest.fixture()
def install_fake_provider(client: TestClient, monkeypatch):
    """Overrides the execute endpoint's provider dependency with a fake, and
    sets a dummy API key so the pre-execution key check passes."""
    from app.experiments.executor import get_llm_provider
    from app.main import app

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    get_settings.cache_clear()

    def _install(provider) -> None:
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield _install

    app.dependency_overrides.pop(get_llm_provider, None)
    get_settings.cache_clear()


class TestExecuteEndpoint:
    def test_execute_returns_execution_summary(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"], repeat_count=2)
        install_fake_provider(
            ScriptedProvider(outcomes=[make_result(VALID_OUTPUT) for _ in range(2)])
        )

        response = client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        assert response.status_code == 200
        body = response.json()
        assert body["experiment_id"] == experiment["id"]
        assert body["status"] == "completed"
        assert body["planned_runs"] == 2
        assert body["completed_runs"] == 2
        assert body["failed_runs"] == 0
        assert body["schema_valid_runs"] == 2
        assert body["schema_invalid_runs"] == 0
        assert body["started_at"] is not None
        assert body["completed_at"] is not None

    def test_execute_missing_experiment_returns_404(self, client: TestClient) -> None:
        response = client.post("/api/v1/experiments/999/execute")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_execute_twice_returns_409(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])
        install_fake_provider(ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)]))
        first = client.post(f"/api/v1/experiments/{experiment['id']}/execute")
        assert first.status_code == 200

        second = client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        assert second.status_code == 409

    def test_execute_unsupported_model_returns_422_and_creates_no_runs(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(
            client, item["id"], prompt["id"], model_names=["gpt-4o-mini"]
        )
        install_fake_provider(ScriptedProvider(outcomes=[]))

        response = client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        assert response.status_code == 422
        runs = client.get(f"/api/v1/experiments/{experiment['id']}/runs").json()
        assert runs == []

    def test_execute_too_many_planned_runs_returns_422_and_creates_no_runs(
        self, client: TestClient, install_fake_provider, monkeypatch
    ) -> None:
        monkeypatch.setenv("MAX_RUNS_PER_EXPERIMENT", "1")
        get_settings.cache_clear()

        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"], repeat_count=2)
        install_fake_provider(ScriptedProvider(outcomes=[]))

        response = client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        assert response.status_code == 422
        runs = client.get(f"/api/v1/experiments/{experiment['id']}/runs").json()
        assert runs == []

    def test_execute_missing_api_key_returns_503_and_creates_no_runs(
        self, client: TestClient
    ) -> None:
        # No install_fake_provider fixture: the default dependency returns
        # None, so this exercises the real "is a key configured?" check.
        # The client fixture already unsets OPENAI_API_KEY.
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])

        response = client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        assert response.status_code == 503
        assert "detail" in response.json()
        runs = client.get(f"/api/v1/experiments/{experiment['id']}/runs").json()
        assert runs == []

    def test_execute_response_never_leaks_api_key(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])
        install_fake_provider(ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)]))

        response = client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        assert "sk-test-dummy-key" not in response.text


class TestExperimentRunListEndpoint:
    def test_returns_runs_in_deterministic_order(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"], repeat_count=3)
        install_fake_provider(
            ScriptedProvider(outcomes=[make_result(VALID_OUTPUT) for _ in range(3)])
        )
        client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        response = client.get(f"/api/v1/experiments/{experiment['id']}/runs")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 3
        assert [run["repetition_index"] for run in body] == [1, 2, 3]
        ids = [run["id"] for run in body]
        assert ids == sorted(ids)

    def test_missing_experiment_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/experiments/999/runs")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_empty_for_unexecuted_draft_experiment(self, client: TestClient) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])

        response = client.get(f"/api/v1/experiments/{experiment['id']}/runs")

        assert response.status_code == 200
        assert response.json() == []


class TestRunDetailEndpoint:
    def test_returns_run_detail(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])
        install_fake_provider(ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)]))
        client.post(f"/api/v1/experiments/{experiment['id']}/execute")
        run_id = client.get(f"/api/v1/experiments/{experiment['id']}/runs").json()[0]["id"]

        response = client.get(f"/api/v1/runs/{run_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == run_id
        assert body["experiment_id"] == experiment["id"]
        assert body["status"] == "completed"
        assert body["raw_response"] == VALID_OUTPUT

    def test_missing_run_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/runs/999")

        assert response.status_code == 404
        assert "detail" in response.json()
