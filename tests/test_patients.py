from tests.conftest import future_birth


def test_list_patients_admin_only(client, patient, admin_headers, patient_headers):
    assert client.get("/api/v1/patients/", headers=patient_headers).status_code == 403
    response = client.get("/api/v1/patients/?q=awa", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["meta"]["total"] == 1


def test_patient_sees_own_profile_only(client, patient, register_patient):
    _, other_headers = register_patient("bob@example.com", "Bob Ba")
    patient_id = patient[0]["profile"]["id"]
    assert client.get(f"/api/v1/patients/{patient_id}", headers=patient[1]).status_code == 200
    assert client.get(f"/api/v1/patients/{patient_id}", headers=other_headers).status_code == 403


def test_get_unknown_patient_returns_404(client, admin_headers):
    assert client.get("/api/v1/patients/999", headers=admin_headers).status_code == 404


def test_patient_updates_profile(client, patient):
    patient_id = patient[0]["profile"]["id"]
    response = client.patch(f"/api/v1/patients/{patient_id}", json={"name": "Awa Diop Sarr"},
                            headers=patient[1])
    assert response.status_code == 200
    assert response.get_json()["name"] == "Awa Diop Sarr"


def test_patient_update_validation(client, patient):
    patient_id = patient[0]["profile"]["id"]
    url = f"/api/v1/patients/{patient_id}"
    assert client.patch(url, json={}, headers=patient[1]).status_code == 422
    assert client.patch(url, json={"date_of_birth": future_birth()},
                        headers=patient[1]).status_code == 422


def test_doctor_cannot_read_patient_profile_directly(client, patient, doctor_headers):
    patient_id = patient[0]["profile"]["id"]
    assert client.get(f"/api/v1/patients/{patient_id}", headers=doctor_headers).status_code == 403