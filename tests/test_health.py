from sqlalchemy.exc import OperationalError

from app.extensions import db


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(client, monkeypatch):
    def broken(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(db.session, "execute", broken)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["database"] == "unreachable"


def test_security_headers_and_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-ID"] == "abc-123"


def test_metrics_counts_requests(client):
    client.get("/health")
    client.get("/api/v1/doctors/999")
    body = client.get("/metrics").get_json()
    assert body["requests_total"] >= 2
    assert "404" in body["requests_by_status"]


def test_swagger_docs_available(client):
    assert client.get("/docs/").status_code == 200
    spec = client.get("/apispec.json").get_json()
    assert spec["openapi"] == "3.0.3"
    assert "/api/v1/appointments/" in spec["paths"]
    assert "bearerAuth" in spec["components"]["securitySchemes"]