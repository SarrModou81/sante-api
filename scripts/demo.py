"""Demonstration du parcours complet de l'API Sante (soutenance).

Usage :
    python scripts/demo.py                          # API locale (python run.py)
    python scripts/demo.py http://127.0.0.1:8000    # API dans Docker

Prerequis : un administrateur existe (flask create-admin --email admin@sante.sn --password motdepasse123).
Aucune dependance : uniquement la bibliotheque standard de Python.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:5000"
ADMIN = {"email": "admin@sante.sn", "password": "motdepasse123"}
RUN = str(int(time.time()))
failures = 0


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    return status, (json.loads(raw) if raw else None)


def step(title, method, path, expected, body=None, token=None):
    global failures
    status, payload = call(method, path, body, token)
    ok = status == expected
    failures += not ok
    detail = payload["error"]["code"] if isinstance(payload, dict) and "error" in payload else ""
    print(f"[{'OK' if ok else 'KO'}] {status} (attendu {expected})  {method:6} {path}  {title}  {detail}")
    return payload


def iso(delta):
    moment = datetime.now(timezone.utc).replace(second=0, microsecond=0) + delta
    return moment.isoformat()


print(f"=== Demo API Sante sur {BASE} ===\n")
step("Healthcheck (teste la base)", "GET", "/health", 200)

print("\n--- 1. Authentification ---")
patient = {"email": f"awa{RUN}@sante.sn", "password": "motdepasse123",
           "name": "Awa Diop", "date_of_birth": "1995-04-12"}
step("Inscription d'un patient", "POST", "/api/v1/auth/register", 201, patient)
step("Inscription avec le meme email", "POST", "/api/v1/auth/register", 409, patient)
step("Tentative de se declarer admin", "POST", "/api/v1/auth/register", 422,
     {**patient, "email": f"x{RUN}@sante.sn", "role": "admin"})
tokens = step("Connexion du patient", "POST", "/api/v1/auth/login", 200,
              {"email": patient["email"], "password": patient["password"]})
patient_token = tokens["access_token"]
step("/me sans jeton", "GET", "/api/v1/auth/me", 401)
step("/me avec jeton", "GET", "/api/v1/auth/me", 200, token=patient_token)
step("Refresh token -> nouveau jeton d'acces", "POST", "/api/v1/auth/refresh", 200,
     token=tokens["refresh_token"])
admin_token = step("Connexion de l'admin", "POST", "/api/v1/auth/login", 200, ADMIN)["access_token"]

print("\n--- 2. Medecins (admin) ---")
doctor = {"email": f"dr.fall{RUN}@sante.sn", "password": "motdepasse123",
          "name": f"Dr Moussa Fall {RUN}", "specialty": "Cardiologie"}
step("Un patient ne peut pas creer de medecin", "POST", "/api/v1/doctors/", 403, doctor, patient_token)
doctor_id = step("L'admin cree un medecin", "POST", "/api/v1/doctors/", 201, doctor, admin_token)["id"]
step("Liste publique paginee + filtre", "GET", "/api/v1/doctors/?specialty=cardiologie&per_page=5", 200)
doctor_token = step("Connexion du medecin", "POST", "/api/v1/auth/login", 200,
                    {"email": doctor["email"], "password": doctor["password"]})["access_token"]

print("\n--- 3. Creneaux (medecin) ---")
slot = {"start_time": iso(timedelta(days=3)), "end_time": iso(timedelta(days=3, minutes=30))}
slot_id = step("Creer un creneau de 30 min dans 3 jours", "POST", "/api/v1/slots/", 201, slot, doctor_token)["id"]
soon = {"start_time": iso(timedelta(hours=2)), "end_time": iso(timedelta(hours=2, minutes=30))}
soon_id = step("Creer un creneau dans 2 h", "POST", "/api/v1/slots/", 201, soon, doctor_token)["id"]
step("Duree de 10 min refusee", "POST", "/api/v1/slots/", 422,
     {"start_time": iso(timedelta(days=5)), "end_time": iso(timedelta(days=5, minutes=10))}, doctor_token)
step("Chevauchement refuse", "POST", "/api/v1/slots/", 409,
     {"start_time": iso(timedelta(days=3, minutes=15)), "end_time": iso(timedelta(days=3, minutes=45))},
     doctor_token)
step("Disponibilites du medecin", "GET", f"/api/v1/doctors/{doctor_id}/slots", 200)

print("\n--- 4. Rendez-vous (patient) ---")
appointment = step("Reserver le creneau", "POST", "/api/v1/appointments/", 201,
                   {"slot_id": slot_id, "reason": "Douleurs thoraciques"}, patient_token)
step("Reserver le meme creneau (double reservation)", "POST", "/api/v1/appointments/", 409,
     {"slot_id": slot_id, "reason": "Encore"}, patient_token)
soon_appointment = step("Reserver le creneau dans 2 h", "POST", "/api/v1/appointments/", 201,
                        {"slot_id": soon_id, "reason": "Consultation"}, patient_token)
step("Le medecin voit ses rendez-vous + infos patient", "GET", "/api/v1/appointments/", 200,
     token=doctor_token)
step("Annuler moins de 24 h avant", "PATCH", f"/api/v1/appointments/{soon_appointment['id']}", 409,
     {"status": "cancelled"}, patient_token)
step("Annuler 3 jours avant", "PATCH", f"/api/v1/appointments/{appointment['id']}", 200,
     {"status": "cancelled"}, patient_token)
step("Historique du patient", "GET",
     f"/api/v1/patients/{appointment['patient']['id']}/appointments", 200, token=patient_token)

print(f"\n=== {'Tout est conforme' if failures == 0 else f'{failures} etape(s) en echec'} ===")
sys.exit(1 if failures else 0)