from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import Doctor, Role, Slot, User
from app.utils import utcnow

PASSWORD = "motdepasse123"


@pytest.fixture
def app():
    app = create_app("test")
    with app.app_context():
        db.create_all()
        yield app  # le test s'execute ici
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, password=PASSWORD):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def make_user(email, role, **profile):
    user = User(email=email, role=role)
    user.set_password(PASSWORD)
    if role == Role.DOCTOR:
        user.doctor = Doctor(name=profile.get("name", "Dr Fall"),
                             specialty=profile.get("specialty", "Cardiologie"))
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def register_patient(client):
    """Fabrique : inscrit un patient via l'API et renvoie (json du compte, en-tetes)."""

    def _register(email="awa@example.com", name="Awa Diop"):
        response = client.post("/api/v1/auth/register", json={
            "email": email, "password": PASSWORD, "name": name, "date_of_birth": "1995-04-12",
        })
        assert response.status_code == 201, response.get_json()
        tokens = login(client, email)
        return response.get_json(), bearer(tokens["access_token"])

    return _register


@pytest.fixture
def patient(register_patient):
    return register_patient()


@pytest.fixture
def patient_headers(patient):
    return patient[1]


@pytest.fixture
def admin_headers(app, client):
    make_user("admin@example.com", Role.ADMIN)
    return bearer(login(client, "admin@example.com")["access_token"])


@pytest.fixture
def doctor(app):
    return make_user("dr.fall@example.com", Role.DOCTOR).doctor


@pytest.fixture
def doctor_headers(client, doctor):
    return bearer(login(client, "dr.fall@example.com")["access_token"])


@pytest.fixture
def other_doctor(app):
    return make_user("dr.ndiaye@example.com", Role.DOCTOR, name="Dr Ndiaye",
                     specialty="Dermatologie").doctor


@pytest.fixture
def make_slot(app):
    """Fabrique : cree un creneau directement en base (y compris dans le passe)."""

    def _make(doctor, start_in=timedelta(days=2), minutes=30, available=True):
        start = (utcnow() + start_in).replace(microsecond=0)
        slot = Slot(doctor_id=doctor.id, start_time=start,
                    end_time=start + timedelta(minutes=minutes), is_available=available)
        db.session.add(slot)
        db.session.commit()
        return slot

    return _make


def iso(delta):
    return (utcnow() + delta).replace(microsecond=0).isoformat()


def future_birth():
    return (date.today() + timedelta(days=1)).isoformat()