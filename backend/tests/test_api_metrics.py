"""API-level tests for the metrics and failures endpoints. Every execution
goes through a fake LLM provider (ScriptedProvider) -- no test here makes
a network call."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.fakes import ScriptedProvider, make_result

VALID_OUTPUT = (
    '{"category": "billing", "priority": "high", "summary": "s", '
    '"recommended_action": "a"}'
)
MISMATCHED_OUTPUT = (
    '{"category": "bug", "priority": "low", "summary": "s", '
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
    from app.experiments.executor import get_llm_provider
    from app.main import app

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    get_settings.cache_clear()

    def _install(provider) -> None:
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield _install

    app.dependency_overrides.pop(get_llm_provider, None)
    get_settings.cache_clear()


class TestMetricsEndpoint:
    def test_metrics_endpoint_success(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"], repeat_count=2)
        install_fake_provider(
            ScriptedProvider(outcomes=[make_result(VALID_OUTPUT) for _ in range(2)])
        )
        client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        response = client.get(f"/api/v1/experiments/{experiment['id']}/metrics")

        assert response.status_code == 200
        body = response.json()
        assert body["experiment_id"] == experiment["id"]
        assert body["experiment_name"] == experiment["name"]
        assert body["status"] == "completed"
        assert body["total_runs"] == 2
        assert len(body["variant_metrics"]) == 1
        variant = body["variant_metrics"][0]
        assert variant["prompt_version_id"] == prompt["id"]
        assert variant["model_name"] == "gpt-5-mini"
        assert variant["average_reliability_score"] == 100.0
        assert variant["category_accuracy"] == 1.0
        assert variant["priority_accuracy"] == 1.0
        assert body["recommendation"]["recommended_prompt_version_id"] == prompt["id"]

    def test_experiment_not_found_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/experiments/999/metrics")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_metrics_before_completion_returns_409(self, client: TestClient) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])

        response = client.get(f"/api/v1/experiments/{experiment['id']}/metrics")

        assert response.status_code == 409
        assert "detail" in response.json()

    def test_metrics_reflects_mixed_outcomes(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"], repeat_count=2)
        install_fake_provider(
            ScriptedProvider(outcomes=[make_result(VALID_OUTPUT), make_result(MISMATCHED_OUTPUT)])
        )

        client.post(f"/api/v1/experiments/{experiment['id']}/execute")
        response = client.get(f"/api/v1/experiments/{experiment['id']}/metrics")

        assert response.status_code == 200
        variant = response.json()["variant_metrics"][0]
        assert variant["schema_valid_runs"] == 2
        assert variant["category_accuracy"] == 0.5
        assert variant["priority_accuracy"] == 0.5
        assert variant["failure_count"] == 1


class TestFailuresEndpoint:
    def test_failures_endpoint_success(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"], repeat_count=2)
        install_fake_provider(
            ScriptedProvider(outcomes=[make_result(VALID_OUTPUT), make_result("not json")])
        )
        client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        response = client.get(f"/api/v1/experiments/{experiment['id']}/failures")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["failure_category"] == "invalid_json"
        assert body[0]["dataset_item_id"] == item["id"]
        assert body[0]["prompt_version_id"] == prompt["id"]

    def test_experiment_not_found_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/experiments/999/failures")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_empty_failures_list_for_all_successful_runs(
        self, client: TestClient, install_fake_provider
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])
        install_fake_provider(ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)]))
        client.post(f"/api/v1/experiments/{experiment['id']}/execute")

        response = client.get(f"/api/v1/experiments/{experiment['id']}/failures")

        assert response.status_code == 200
        assert response.json() == []

    def test_empty_failures_list_for_unexecuted_draft_experiment(
        self, client: TestClient
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        experiment = _create_experiment(client, item["id"], prompt["id"])

        response = client.get(f"/api/v1/experiments/{experiment['id']}/failures")

        assert response.status_code == 200
        assert response.json() == []
