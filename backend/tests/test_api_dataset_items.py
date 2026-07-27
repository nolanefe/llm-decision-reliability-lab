from fastapi.testclient import TestClient


def _payload(**overrides) -> dict:
    payload = dict(
        name="billing-refund",
        input_text="I was charged twice for my subscription.",
        expected_category="billing",
        expected_priority="high",
    )
    payload.update(overrides)
    return payload


class TestListDatasetItems:
    def test_list_empty_returns_empty_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/dataset-items")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_created_items(self, client: TestClient) -> None:
        client.post("/api/v1/dataset-items", json=_payload())
        client.post("/api/v1/dataset-items", json=_payload(name="bug-report"))

        response = client.get("/api/v1/dataset-items")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestCreateDatasetItem:
    def test_create_returns_201_with_body(self, client: TestClient) -> None:
        response = client.post("/api/v1/dataset-items", json=_payload())
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "billing-refund"
        assert body["expected_category"] == "billing"
        assert body["expected_priority"] == "high"
        assert "id" in body
        assert "created_at" in body

    def test_create_rejects_blank_name(self, client: TestClient) -> None:
        response = client.post("/api/v1/dataset-items", json=_payload(name="   "))
        assert response.status_code == 422

    def test_create_rejects_invalid_category(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/dataset-items", json=_payload(expected_category="not_a_category")
        )
        assert response.status_code == 422


class TestGetDatasetItem:
    def test_get_returns_matching_item(self, client: TestClient) -> None:
        created = client.post("/api/v1/dataset-items", json=_payload()).json()

        response = client.get(f"/api/v1/dataset-items/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_missing_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/dataset-items/999")
        assert response.status_code == 404
        assert "detail" in response.json()
