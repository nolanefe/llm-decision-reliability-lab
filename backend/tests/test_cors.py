from fastapi.testclient import TestClient


class TestCorsHeaders:
    def test_allowed_localhost_origin_receives_cors_headers(
        self, client: TestClient
    ) -> None:
        response = client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    def test_unlisted_origin_does_not_receive_allow_origin_header(
        self, client: TestClient
    ) -> None:
        response = client.get(
            "/health", headers={"Origin": "http://evil.example.com"}
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
