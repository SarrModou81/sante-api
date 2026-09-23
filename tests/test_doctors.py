from datetime import timedelta

from tests.conftest import PASSWORD

NEW_DOCTOR = {"email": "dr.sow@example.com", "password": PASSWORD,
              "name": "Dr Aminata Sow", "specialty": "Pediatrie"}


def test_list_doctors_is_public_and_paginated(client, doctor, other_doctor):
    response = client.get("/api/v1/doctors/?per_page=1")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["items"]) == 1
    assert body["meta"] == {"page": 1, "per_page": 1, "pages": 2, "total": 2}


def test_list_doctors_filter_search_and_sort(client, doctor, other_doctor):
    body = client.get("/api/v1/doctors/?specialty=dermatologie").get_json()
    assert [d["name"] for d in body["items"]] == ["Dr Ndiaye"]
    body = client.get("/api/v1/doctors/?q=fall").get_json()
    assert [d["name"] for d in body["items"]] == ["Dr Fall"]
    body = client.get("/api/v1/doctors/?sort=-name").get_json()
    assert [d["name"] for d in body["items"]] == ["Dr Ndiaye", "Dr Fall"]


def test_list_doctors_invalid_sort_returns_422(client):
    assert client.get("/api/v1/doctors/?sort=email").status_code == 422


def test_per_page_is_capped_at_100(client, doctor):
    body = client.get("/api/v1/doctors/?per_page=10000").get_json()
    assert body["meta"]["per_page"] == 100


def test_get_doctor_and_404(client, doctor):
    response = client.get(f"/api/v1/doctors/{doctor.id}")
    assert response.status_code == 200
    assert response.get_json()["email"] == "dr.fall@example.com"
    assert client.get("/api/v1/doctors/999").status_code == 404


def test_create_doctor_requires_token(client):
    assert client.post("/api/v1/doctors/", json=NEW_DOCTOR).status_code == 401


def test_create_doctor_forbidden_for_patient(client, patient_headers):
    response = client.post("/api/v1/doctors/", json=NEW_DOCTOR, headers=patient_headers)
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


def test_admin_creates_doctor_who_can_login(client, admin_headers):
    response = client.post("/api/v1/doctors/", json=NEW_DOCTOR, headers=admin_headers)
    assert response.status_code == 201
    assert response.get_json()["specialty"] == "Pediatrie"
    login = client.post("/api/v1/auth/login",
                        json={"email": NEW_DOCTOR["email"], "password": PASSWORD})
    assert login.status_code == 200


def test_create_doctor_duplicate_email_returns_409(client, admin_headers, doctor):
    payload = dict(NEW_DOCTOR, email="dr.fall@example.com")
    assert client.post("/api/v1/doctors/", json=payload, headers=admin_headers).status_code == 409


def test_doctor_updates_own_profile_only(client, doctor, other_doctor, doctor_headers):
    response = client.patch(f"/api/v1/doctors/{doctor.id}", json={"specialty": "Cardio"},
                            headers=doctor_headers)
    assert response.status_code == 200
    assert response.get_json()["specialty"] == "Cardio"
    response = client.patch(f"/api/v1/doctors/{other_doctor.id}", json={"name": "Pirate"},
                            headers=doctor_headers)
    assert response.status_code == 403


def test_update_doctor_empty_body_returns_422(client, doctor, admin_headers):
    response = client.patch(f"/api/v1/doctors/{doctor.id}", json={}, headers=admin_headers)
    assert response.status_code == 422


def test_admin_deletes_doctor(client, doctor, admin_headers, make_slot):
    make_slot(doctor)
    assert client.delete(f"/api/v1/doctors/{doctor.id}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/v1/doctors/{doctor.id}").status_code == 404


def test_delete_doctor_forbidden_for_doctor(client, doctor, doctor_headers):
    assert client.delete(f"/api/v1/doctors/{doctor.id}", headers=doctor_headers).status_code == 403


def test_delete_doctor_with_appointments_returns_409(client, doctor, admin_headers, make_slot,
                                                     patient_headers):
    slot = make_slot(doctor)
    client.post("/api/v1/appointments/", json={"slot_id": slot.id, "reason": "Controle"},
                headers=patient_headers)
    response = client.delete(f"/api/v1/doctors/{doctor.id}", headers=admin_headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "doctor_has_appointments"


def test_doctor_availabilities_show_only_free_future_slots(client, doctor, make_slot):
    free = make_slot(doctor, start_in=timedelta(days=1))
    make_slot(doctor, start_in=timedelta(days=2), available=False)
    make_slot(doctor, start_in=-timedelta(days=1))
    body = client.get(f"/api/v1/doctors/{doctor.id}/slots").get_json()
    assert [s["id"] for s in body["items"]] == [free.id]
    assert client.get("/api/v1/doctors/999/slots").status_code == 404


def test_doctor_cannot_list_patients(client, doctor_headers):
    assert client.get("/api/v1/patients/", headers=doctor_headers).status_code == 403