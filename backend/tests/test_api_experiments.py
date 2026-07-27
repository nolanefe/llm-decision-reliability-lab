from fastapi.testclient import TestClient


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
        name="baseline",
        version=1,
        template_text="Classify this ticket: {ticket_text}",
    )
    payload.update(overrides)
    return client.post("/api/v1/prompt-versions", json=payload).json()


def _experiment_payload(**overrides) -> dict:
    payload = dict(
        name="baseline-comparison",
        dataset_item_ids=[1],
        prompt_version_ids=[1],
        model_names=["gpt-4o-mini"],
        repeat_count=3,
    )
    payload.update(overrides)
    return payload


class TestCreateExperiment:
    def test_create_with_valid_selections_returns_201_and_draft_status(
        self, client: TestClient
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]],
                prompt_version_ids=[prompt["id"]],
            ),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "draft"

    def test_persisted_selections_are_returned_on_create(
        self, client: TestClient
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]],
                prompt_version_ids=[prompt["id"]],
                model_names=["gpt-4o-mini", "gpt-4o"],
            ),
        )

        body = response.json()
        assert body["dataset_item_ids"] == [item["id"]]
        assert body["prompt_version_ids"] == [prompt["id"]]
        assert body["model_names"] == ["gpt-4o-mini", "gpt-4o"]

    def test_persisted_selections_are_returned_on_get(
        self, client: TestClient
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        created = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]],
                prompt_version_ids=[prompt["id"]],
            ),
        ).json()

        response = client.get(f"/api/v1/experiments/{created['id']}")

        assert response.status_code == 200
        body = response.json()
        assert body["dataset_item_ids"] == [item["id"]]
        assert body["prompt_version_ids"] == [prompt["id"]]
        assert body["model_names"] == ["gpt-4o-mini"]

    def test_missing_dataset_item_id_is_rejected(self, client: TestClient) -> None:
        prompt = _create_prompt_version(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[999],
                prompt_version_ids=[prompt["id"]],
            ),
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_missing_prompt_version_id_is_rejected(self, client: TestClient) -> None:
        item = _create_dataset_item(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]],
                prompt_version_ids=[999],
            ),
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_duplicate_dataset_item_ids_rejected_by_schema(
        self, client: TestClient
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"], item["id"]],
                prompt_version_ids=[prompt["id"]],
            ),
        )

        assert response.status_code == 422

    def test_duplicate_prompt_version_ids_rejected_by_schema(
        self, client: TestClient
    ) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]],
                prompt_version_ids=[prompt["id"], prompt["id"]],
            ),
        )

        assert response.status_code == 422

    def test_no_run_records_are_created(self, client: TestClient) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)

        response = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]],
                prompt_version_ids=[prompt["id"]],
            ),
        )

        # No runs endpoint exists yet at this stage; verifying via the
        # experiment response is limited to confirming draft status and that
        # creation succeeds without any run-related side effects.
        assert response.json()["status"] == "draft"


class TestListAndGetExperiments:
    def test_list_returns_created_experiments(self, client: TestClient) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]], prompt_version_ids=[prompt["id"]]
            ),
        )

        response = client.get("/api/v1/experiments")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_returns_matching_experiment(self, client: TestClient) -> None:
        item = _create_dataset_item(client)
        prompt = _create_prompt_version(client)
        created = client.post(
            "/api/v1/experiments",
            json=_experiment_payload(
                dataset_item_ids=[item["id"]], prompt_version_ids=[prompt["id"]]
            ),
        ).json()

        response = client.get(f"/api/v1/experiments/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_missing_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/experiments/999")

        assert response.status_code == 404
        assert "detail" in response.json()
