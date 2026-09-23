import pytest

from app import create_app
from app.config import DEV_SECRET


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.is_json
    error = response.get_json()["error"]
    assert error["status"] == status
    assert error["code"] == code
    assert set(error) == {"status", "code", "message", "details", "request_id"}
    return error


def test_unknown_route_returns_json_404(client):
    assert_error(client.get("/nexiste-pas"), 404, "not_found")


def test_method_not_allowed_returns_json_405(client):
    assert_error(client.put("/health"), 405, "method_not_allowed")


def test_invalid_json_returns_400(client):
    response = client.post("/api/v1/auth/register", data="pas du json",
                           content_type="application/json")
    assert_error(response, 400, "invalid_json")


def test_validation_error_returns_422_with_details(client):
    error = assert_error(client.post("/api/v1/auth/register", json={}), 422, "validation_error")
    assert "email" in error["details"]
    assert "password" in error["details"]


def test_unexpected_exception_returns_generic_500(app, client):
    @app.get("/boom")
    def boom():
        raise RuntimeError("detail technique secret")

    error = assert_error(client.get("/boom"), 500, "internal_server_error")
    assert "secret" not in error["message"]


def test_prod_refuses_default_secrets(monkeypatch):
    monkeypatch.setattr("app.config.ProdConfig.SECRET_KEY", DEV_SECRET)
    with pytest.raises(RuntimeError):
        create_app("prod")


def test_prod_has_no_debug_and_no_swagger(monkeypatch):
    monkeypatch.setattr("app.config.ProdConfig.SECRET_KEY", "un-vrai-secret-de-production-tres-long")
    monkeypatch.setattr("app.config.ProdConfig.JWT_SECRET_KEY", "un-vrai-secret-jwt-de-production-tres-long")
    monkeypatch.setattr("app.config.ProdConfig.SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    app = create_app("prod")
    assert app.config["DEBUG"] is False
    assert app.test_client().get("/docs/").status_code == 404