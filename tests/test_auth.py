from datetime import timedelta

from flask_jwt_extended import create_access_token

from app.config import TestConfig
from tests.conftest import PASSWORD, bearer, future_birth, login


def test_register_creates_patient(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "Awa@Example.com", "password": PASSWORD, "name": "Awa Diop",
        "date_of_birth": "1995-04-12",
    })
    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "awa@example.com"  # email normalise
    assert body["role"] == "patient"
    assert body["profile"]["name"] == "Awa Diop"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_returns_409(client, patient):
    response = client.post("/api/v1/auth/register", json={
        "email": "awa@example.com", "password": PASSWORD, "name": "Autre",
        "date_of_birth": "1990-01-01",
    })
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "email_taken"


def test_register_rejects_short_password_and_future_birth(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "x@example.com", "password": "court", "name": "X Y",
        "date_of_birth": future_birth(),
    })
    assert response.status_code == 422
    details = response.get_json()["error"]["details"]
    assert "password" in details and "date_of_birth" in details


def test_register_rejects_unknown_field(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "x@example.com", "password": PASSWORD, "name": "X Y",
        "date_of_birth": "1990-01-01", "role": "admin",
    })
    assert response.status_code == 422
    assert "role" in response.get_json()["error"]["details"]


def test_login_returns_access_and_refresh_tokens(client, patient):
    tokens = login(client, "awa@example.com")
    assert tokens["token_type"] == "Bearer"
    assert tokens["access_token"] and tokens["refresh_token"]


def test_login_wrong_password_returns_401(client, patient):
    response = client.post("/api/v1/auth/login",
                           json={"email": "awa@example.com", "password": "mauvais-mdp"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_email_returns_401(client):
    response = client.post("/api/v1/auth/login",
                           json={"email": "inconnu@example.com", "password": PASSWORD})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "missing_token"


def test_me_with_invalid_token_returns_401(client):
    response = client.get("/api/v1/auth/me", headers=bearer("pas.un.jeton"))
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_token"


def test_me_with_expired_token_returns_401(app, client, patient):
    token = create_access_token(identity="1", expires_delta=timedelta(seconds=-1))
    response = client.get("/api/v1/auth/me", headers=bearer(token))
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "token_expired"


def test_me_with_token_of_deleted_user_returns_401(app, client):
    token = create_access_token(identity="999")
    response = client.get("/api/v1/auth/me", headers=bearer(token))
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "user_not_found"


def test_me_returns_current_user(client, patient_headers):
    response = client.get("/api/v1/auth/me", headers=patient_headers)
    assert response.status_code == 200
    assert response.get_json()["email"] == "awa@example.com"


def test_me_for_doctor_and_admin(client, doctor_headers, admin_headers):
    assert client.get("/api/v1/auth/me", headers=doctor_headers).get_json()["profile"]["specialty"]
    assert client.get("/api/v1/auth/me", headers=admin_headers).get_json()["profile"] is None


def test_refresh_gives_new_access_token(client, patient):
    tokens = login(client, "awa@example.com")
    response = client.post("/api/v1/auth/refresh", headers=bearer(tokens["refresh_token"]))
    assert response.status_code == 200
    new_token = response.get_json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=bearer(new_token)).status_code == 200


def test_refresh_rejects_access_token(client, patient):
    tokens = login(client, "awa@example.com")
    response = client.post("/api/v1/auth/refresh", headers=bearer(tokens["access_token"]))
    assert response.status_code == 401


def test_login_is_rate_limited(monkeypatch):
    monkeypatch.setattr(TestConfig, "RATELIMIT_ENABLED", True)
    from app import create_app
    from app.extensions import db

    app = create_app("test")
    with app.app_context():
        db.create_all()
        client = app.test_client()
        payload = {"email": "x@example.com", "password": "mauvais"}
        statuses = [client.post("/api/v1/auth/login", json=payload).status_code for _ in range(6)]
        assert statuses[:5] == [401] * 5
        assert statuses[5] == 429
        db.drop_all()