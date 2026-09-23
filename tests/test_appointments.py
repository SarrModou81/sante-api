from datetime import timedelta

URL = "/api/v1/appointments/"


def book(client, headers, slot_id, reason="Douleurs thoraciques"):
    return client.post(URL, json={"slot_id": slot_id, "reason": reason}, headers=headers)


def test_patient_books_free_slot(client, doctor, make_slot, patient_headers):
    slot = make_slot(doctor)
    response = book(client, patient_headers, slot.id)
    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "booked"
    assert body["slot"]["id"] == slot.id
    assert body["slot"]["is_available"] is False
    assert body["patient"]["name"] == "Awa Diop"


def test_booking_requires_token(client, doctor, make_slot):
    slot = make_slot(doctor)
    assert client.post(URL, json={"slot_id": slot.id, "reason": "abc"}).status_code == 401


def test_only_patients_can_book(client, doctor, make_slot, doctor_headers):
    slot = make_slot(doctor)
    assert book(client, doctor_headers, slot.id).status_code == 403


def test_already_booked_slot_returns_409(client, doctor, make_slot, patient_headers, register_patient):
    slot = make_slot(doctor)
    assert book(client, patient_headers, slot.id).status_code == 201
    _, other_headers = register_patient("bob@example.com", "Bob Ba")
    response = book(client, other_headers, slot.id)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "slot_already_booked"


def test_booking_past_slot_returns_409(client, doctor, make_slot, patient_headers):
    slot = make_slot(doctor, start_in=-timedelta(hours=1))
    response = book(client, patient_headers, slot.id)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "slot_in_past"


def test_booking_unknown_slot_returns_404(client, patient_headers):
    assert book(client, patient_headers, 999).status_code == 404


def test_booking_validation(client, patient_headers):
    response = client.post(URL, json={"slot_id": "abc"}, headers=patient_headers)
    assert response.status_code == 422
    assert set(response.get_json()["error"]["details"]) == {"slot_id", "reason"}


def test_patient_sees_only_own_appointments(client, doctor, make_slot, patient_headers,
                                            register_patient):
    mine = book(client, patient_headers, make_slot(doctor, start_in=timedelta(days=2)).id).get_json()
    _, other_headers = register_patient("bob@example.com", "Bob Ba")
    other = book(client, other_headers, make_slot(doctor, start_in=timedelta(days=3)).id).get_json()

    body = client.get(URL, headers=patient_headers).get_json()
    assert [a["id"] for a in body["items"]] == [mine["id"]]
    assert client.get(f"{URL}{other['id']}", headers=patient_headers).status_code == 403
    assert client.get(f"{URL}{mine['id']}", headers=patient_headers).status_code == 200


def test_doctor_sees_own_appointments_with_patient_info(client, doctor, other_doctor, make_slot,
                                                        patient_headers, doctor_headers):
    mine = book(client, patient_headers, make_slot(doctor).id).get_json()
    other = book(client, patient_headers, make_slot(other_doctor).id).get_json()

    body = client.get(URL, headers=doctor_headers).get_json()
    assert [a["id"] for a in body["items"]] == [mine["id"]]
    assert body["items"][0]["patient"]["email"] == "awa@example.com"
    assert body["items"][0]["patient"]["date_of_birth"] == "1995-04-12"
    assert client.get(f"{URL}{other['id']}", headers=doctor_headers).status_code == 403


def test_admin_sees_all_and_filters_by_status(client, doctor, make_slot, patient_headers,
                                              admin_headers):
    first = book(client, patient_headers, make_slot(doctor, start_in=timedelta(days=3)).id).get_json()
    book(client, patient_headers, make_slot(doctor, start_in=timedelta(days=4)).id)
    client.patch(f"{URL}{first['id']}", json={"status": "cancelled"}, headers=patient_headers)

    assert client.get(URL, headers=admin_headers).get_json()["meta"]["total"] == 2
    body = client.get(f"{URL}?status=cancelled", headers=admin_headers).get_json()
    assert [a["id"] for a in body["items"]] == [first["id"]]
    body = client.get(f"{URL}?sort=-start_time", headers=admin_headers).get_json()
    assert body["items"][1]["id"] == first["id"]


def test_get_unknown_appointment_returns_404(client, admin_headers):
    assert client.get(f"{URL}999", headers=admin_headers).status_code == 404


def test_cancel_frees_the_slot(client, doctor, make_slot, patient_headers, register_patient):
    slot = make_slot(doctor, start_in=timedelta(days=2))
    appointment = book(client, patient_headers, slot.id).get_json()

    response = client.patch(f"{URL}{appointment['id']}", json={"status": "cancelled"},
                            headers=patient_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "cancelled"
    assert body["cancelled_at"] is not None
    assert body["slot"]["is_available"] is True

    _, other_headers = register_patient("bob@example.com", "Bob Ba")
    assert book(client, other_headers, slot.id).status_code == 201


def test_cancel_less_than_24h_before_returns_409(client, doctor, make_slot, patient_headers):
    slot = make_slot(doctor, start_in=timedelta(hours=23))
    appointment = book(client, patient_headers, slot.id).get_json()
    response = client.patch(f"{URL}{appointment['id']}", json={"status": "cancelled"},
                            headers=patient_headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "cancellation_too_late"


def test_cancel_twice_returns_409(client, doctor, make_slot, patient_headers):
    appointment = book(client, patient_headers, make_slot(doctor).id).get_json()
    url = f"{URL}{appointment['id']}"
    assert client.patch(url, json={"status": "cancelled"}, headers=patient_headers).status_code == 200
    response = client.patch(url, json={"status": "cancelled"}, headers=patient_headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "already_cancelled"


def test_cancel_invalid_status_returns_422(client, doctor, make_slot, patient_headers):
    appointment = book(client, patient_headers, make_slot(doctor).id).get_json()
    response = client.patch(f"{URL}{appointment['id']}", json={"status": "booked"},
                            headers=patient_headers)
    assert response.status_code == 422


def test_doctor_can_cancel_own_appointment(client, doctor, make_slot, patient_headers,
                                           doctor_headers):
    appointment = book(client, patient_headers, make_slot(doctor).id).get_json()
    response = client.patch(f"{URL}{appointment['id']}", json={"status": "cancelled"},
                            headers=doctor_headers)
    assert response.status_code == 200


def test_patient_history(client, doctor, make_slot, patient, register_patient, admin_headers):
    patient_json, headers = patient
    patient_id = patient_json["profile"]["id"]
    book(client, headers, make_slot(doctor, start_in=timedelta(days=2)).id)
    book(client, headers, make_slot(doctor, start_in=timedelta(days=5)).id)

    url = f"/api/v1/patients/{patient_id}/appointments?sort=-start_time"
    body = client.get(url, headers=headers).get_json()
    assert body["meta"]["total"] == 2
    assert body["items"][0]["slot"]["start_time"] > body["items"][1]["slot"]["start_time"]
    assert client.get(f"{url}&status=cancelled", headers=admin_headers).get_json()["meta"]["total"] == 0

    _, other_headers = register_patient("bob@example.com", "Bob Ba")
    assert client.get(url, headers=other_headers).status_code == 403