from datetime import timedelta

from tests.conftest import iso


def slot_payload(start_in=timedelta(days=3), minutes=30):
    return {"start_time": iso(start_in), "end_time": iso(start_in + timedelta(minutes=minutes))}


def test_doctor_creates_own_slot(client, doctor, doctor_headers):
    response = client.post("/api/v1/slots/", json=slot_payload(), headers=doctor_headers)
    assert response.status_code == 201
    body = response.get_json()
    assert body["doctor_id"] == doctor.id
    assert body["duration_minutes"] == 30
    assert body["is_available"] is True
    assert body["doctor"]["name"] == "Dr Fall"


def test_slot_accepts_timezone_and_stores_utc(client, doctor_headers):
    payload = {"start_time": "2099-01-15T10:00:00+02:00", "end_time": "2099-01-15T10:30:00+02:00"}
    body = client.post("/api/v1/slots/", json=payload, headers=doctor_headers).get_json()
    assert body["start_time"] == "2099-01-15T08:00:00"


def test_patient_cannot_create_slot(client, patient_headers):
    assert client.post("/api/v1/slots/", json=slot_payload(), headers=patient_headers).status_code == 403


def test_create_slot_requires_token(client):
    assert client.post("/api/v1/slots/", json=slot_payload()).status_code == 401


def test_start_must_be_before_end(client, doctor_headers):
    payload = slot_payload()
    payload["start_time"], payload["end_time"] = payload["end_time"], payload["start_time"]
    response = client.post("/api/v1/slots/", json=payload, headers=doctor_headers)
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "invalid_slot_window"


def test_duration_between_15_and_120_minutes(client, doctor_headers):
    too_short = client.post("/api/v1/slots/", json=slot_payload(minutes=10), headers=doctor_headers)
    too_long = client.post("/api/v1/slots/", json=slot_payload(minutes=150), headers=doctor_headers)
    assert too_short.status_code == too_long.status_code == 422
    assert too_short.get_json()["error"]["code"] == "invalid_slot_duration"
    for minutes in (15, 120):
        start = timedelta(days=10 + minutes)
        ok = client.post("/api/v1/slots/", json=slot_payload(start, minutes), headers=doctor_headers)
        assert ok.status_code == 201


def test_slot_in_past_is_rejected(client, doctor_headers):
    response = client.post("/api/v1/slots/", json=slot_payload(start_in=-timedelta(days=1)),
                           headers=doctor_headers)
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "slot_in_past"


def test_missing_fields_returns_422(client, doctor_headers):
    response = client.post("/api/v1/slots/", json={"start_time": "pas une date"}, headers=doctor_headers)
    assert response.status_code == 422
    assert set(response.get_json()["error"]["details"]) == {"start_time", "end_time"}


def test_overlapping_slot_returns_409(client, doctor_headers):
    client.post("/api/v1/slots/", json=slot_payload(), headers=doctor_headers)
    overlap = slot_payload(start_in=timedelta(days=3, minutes=15))
    response = client.post("/api/v1/slots/", json=overlap, headers=doctor_headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "slot_overlap"


def test_admin_must_give_doctor_id(client, admin_headers, doctor):
    response = client.post("/api/v1/slots/", json=slot_payload(), headers=admin_headers)
    assert response.status_code == 422
    payload = dict(slot_payload(), doctor_id=doctor.id)
    assert client.post("/api/v1/slots/", json=payload, headers=admin_headers).status_code == 201
    payload = dict(slot_payload(), doctor_id=999)
    assert client.post("/api/v1/slots/", json=payload, headers=admin_headers).status_code == 404


def test_doctor_cannot_create_slot_for_another_doctor(client, doctor_headers, other_doctor):
    payload = dict(slot_payload(), doctor_id=other_doctor.id)
    assert client.post("/api/v1/slots/", json=payload, headers=doctor_headers).status_code == 403


def test_list_slots_filters_and_sort(client, doctor, other_doctor, make_slot):
    first = make_slot(doctor, start_in=timedelta(days=1))
    second = make_slot(doctor, start_in=timedelta(days=2), available=False)
    make_slot(other_doctor, start_in=timedelta(days=3))

    body = client.get(f"/api/v1/slots/?doctor_id={doctor.id}&sort=-start_time").get_json()
    assert [s["id"] for s in body["items"]] == [second.id, first.id]
    body = client.get(f"/api/v1/slots/?doctor_id={doctor.id}&available=true").get_json()
    assert [s["id"] for s in body["items"]] == [first.id]
    date_to = iso(timedelta(days=1, hours=12))
    body = client.get("/api/v1/slots/", query_string={"date_to": date_to}).get_json()
    assert [s["id"] for s in body["items"]] == [first.id]
    date_from = iso(timedelta(days=1, hours=12))
    body = client.get("/api/v1/slots/", query_string={"date_from": date_from}).get_json()
    assert body["meta"]["total"] == 2


def test_list_slots_invalid_filter_returns_422(client):
    assert client.get("/api/v1/slots/?date_from=hier").status_code == 422
    assert client.get("/api/v1/slots/?page=0").status_code == 422


def test_get_slot_and_404(client, doctor, make_slot):
    slot = make_slot(doctor)
    assert client.get(f"/api/v1/slots/{slot.id}").status_code == 200
    assert client.get("/api/v1/slots/999").status_code == 404


def test_update_slot(client, doctor, doctor_headers, make_slot):
    slot = make_slot(doctor)
    new_end = iso(timedelta(days=2, minutes=45))
    response = client.patch(f"/api/v1/slots/{slot.id}", json={"end_time": new_end},
                            headers=doctor_headers)
    assert response.status_code == 200
    assert response.get_json()["duration_minutes"] == 45
    assert client.patch(f"/api/v1/slots/{slot.id}", json={}, headers=doctor_headers).status_code == 422


def test_update_slot_of_other_doctor_is_forbidden(client, other_doctor, doctor_headers, make_slot):
    slot = make_slot(other_doctor)
    response = client.patch(f"/api/v1/slots/{slot.id}", json={"end_time": iso(timedelta(days=2, minutes=45))},
                            headers=doctor_headers)
    assert response.status_code == 403


def test_update_booked_slot_returns_409(client, doctor, doctor_headers, make_slot):
    slot = make_slot(doctor, available=False)
    response = client.patch(f"/api/v1/slots/{slot.id}", json={"end_time": iso(timedelta(days=2, minutes=45))},
                            headers=doctor_headers)
    assert response.status_code == 409


def test_delete_slot(client, doctor, doctor_headers, admin_headers, make_slot):
    slot = make_slot(doctor)
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=doctor_headers).status_code == 204
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=admin_headers).status_code == 404


def test_delete_slot_with_appointment_returns_409(client, doctor, doctor_headers, make_slot,
                                                  patient_headers):
    slot = make_slot(doctor)
    client.post("/api/v1/appointments/", json={"slot_id": slot.id, "reason": "Controle"},
                headers=patient_headers)
    response = client.delete(f"/api/v1/slots/{slot.id}", headers=doctor_headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "slot_has_appointments"