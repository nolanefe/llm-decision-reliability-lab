from fastapi.testclient import TestClient


def _payload(**overrides) -> dict:
    payload = dict(
        name="baseline",
        version=1,
        template_text="Classify this ticket: {ticket_text}",
    )
    payload.update(overrides)
    return payload


class TestListPromptVersions:
    def test_list_empty_returns_empty_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/prompt-versions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_created_versions(self, client: TestClient) -> None:
        client.post("/api/v1/prompt-versions", json=_payload())
        client.post("/api/v1/prompt-versions", json=_payload(version=2))

        response = client.get("/api/v1/prompt-versions")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestCreatePromptVersion:
    def test_create_returns_201_with_body(self, client: TestClient) -> None:
        response = client.post("/api/v1/prompt-versions", json=_payload())
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "baseline"
        assert body["version"] == 1
        assert "id" in body

    def test_create_rejects_missing_ticket_text_placeholder(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/prompt-versions",
            json=_payload(template_text="Classify this ticket without a placeholder."),
        )
        assert response.status_code == 422

    def test_duplicate_name_and_version_returns_409(self, client: TestClient) -> None:
        client.post("/api/v1/prompt-versions", json=_payload())
        response = client.post("/api/v1/prompt-versions", json=_payload())

        assert response.status_code == 409
        assert "detail" in response.json()

    def test_same_name_different_version_allowed(self, client: TestClient) -> None:
        client.post("/api/v1/prompt-versions", json=_payload(version=1))
        response = client.post("/api/v1/prompt-versions", json=_payload(version=2))

        assert response.status_code == 201


class TestGetPromptVersion:
    def test_get_returns_matching_version(self, client: TestClient) -> None:
        created = client.post("/api/v1/prompt-versions", json=_payload()).json()

        response = client.get(f"/api/v1/prompt-versions/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_missing_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/prompt-versions/999")
        assert response.status_code == 404
        assert "detail" in response.json()
