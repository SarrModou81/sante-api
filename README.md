# API Santé — Téléconsultation

API REST Flask de prise de rendez-vous médicaux : des **médecins** publient des **créneaux**, des **patients** les réservent et peuvent annuler jusqu'à 24 h avant.

Projet final du cours *Conception d'API REST avec Flask* — **Sujet D**.

| | |
|---|---|
| Architecture | App factory, blueprints versionnés (`/api/v1`), couches modèles / schémas / services / routes |
| Persistance | SQLAlchemy + migrations Alembic (SQLite en dev, PostgreSQL en Docker) |
| Validation | Marshmallow sur toutes les entrées et sorties |
| Sécurité | JWT (accès + rafraîchissement), 3 rôles, rate limiting, CORS, en-têtes de sécurité |
| Qualité | 87 tests pytest, couverture 99 %, erreurs JSON uniformes |
| Documentation | OpenAPI 3 générée depuis Marshmallow, Swagger UI sur `/docs/` |
| Déploiement | Docker (Gunicorn, 4 workers) + docker-compose avec PostgreSQL |

Les choix de conception (contrat HTTP, codes d'erreur, modèle de données) sont justifiés dans [`docs/CONCEPTION.md`](docs/CONCEPTION.md).

---

## Règles métier

| Règle | Réponse |
|---|---|
| Un créneau déjà réservé ne peut pas l'être une seconde fois (UPDATE atomique) | `409 slot_already_booked` |
| Annulation possible jusqu'à 24 h avant le rendez-vous | `409 cancellation_too_late` |
| Un patient ne voit que ses propres rendez-vous | `403` |
| Un médecin voit tous ses rendez-vous, avec les informations des patients | `200` |
| `start_time < end_time` et durée entre 15 et 120 minutes | `422` |
| Pas de chevauchement de créneaux pour un même médecin | `409 slot_overlap` |

## Rôles

| Rôle | Obtenu par | Peut |
|---|---|---|
| `patient` | `POST /api/v1/auth/register` | réserver, annuler, voir son profil et son historique |
| `doctor` | créé par un admin (`POST /api/v1/doctors/`) | gérer ses créneaux, voir ses rendez-vous |
| `admin` | commande `flask create-admin` uniquement | gérer les médecins, voir tous les patients et rendez-vous |

---

## Installation (développement)

Prérequis : Python 3.12+ (testé jusqu'à 3.14).

```powershell
git clone <url-du-depot> sante-api
cd sante-api
python -m venv .venv
.venv\Scripts\Activate.ps1          # Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env         # Linux/macOS : cp .env.example .env
```

Dans `.env`, remplacer `SECRET_KEY` et `JWT_SECRET_KEY` par des valeurs aléatoires :

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Créer la base et un administrateur :

```powershell
flask db upgrade
flask create-admin --email admin@sante.sn --password motdepasse123
```

## Lancement

```powershell
python run.py
```

- API : http://127.0.0.1:5000/api/v1/
- Healthcheck : http://127.0.0.1:5000/health
- **Swagger UI** : http://127.0.0.1:5000/docs/ (mode développement uniquement)
- Spécification OpenAPI : http://127.0.0.1:5000/apispec.json

## Tests

```powershell
pytest -v
pytest --cov=app --cov-report=term-missing
```

Les tests utilisent une base SQLite en mémoire recréée pour chaque test : aucune configuration manuelle n'est nécessaire.

## Démonstration du parcours complet

Avec l'API lancée et l'admin créé :

```powershell
python scripts/demo.py                          # API locale
python scripts/demo.py http://127.0.0.1:8000    # API dans Docker
```

Le script (bibliothèque standard uniquement) enchaîne : inscription, connexion, refresh, création d'un médecin par l'admin, création de créneaux, réservation, double réservation (409), annulation trop tardive (409), annulation, historique. Chaque étape affiche le code obtenu et le code attendu.

> Le login est limité à 5 requêtes par minute : attendre une minute entre deux exécutions.

## Déploiement avec Docker

```powershell
docker compose up -d --build
docker compose exec api flask create-admin --email admin@sante.sn --password motdepasse123
curl.exe http://127.0.0.1:8000/health
```

`docker compose up` démarre PostgreSQL, attend qu'il soit prêt, applique les migrations puis lance Gunicorn (4 workers) sur le port 8000. Les secrets sont lus depuis `.env`. Swagger est désactivé en production.

```powershell
docker compose down        # arrêt (données conservées dans le volume pgdata)
docker compose down -v     # arrêt + suppression de la base
```

---

## Endpoints

| Méthode | URL | Accès | Succès |
|---|---|---|---|
| GET | `/health` | public | 200 / 503 |
| GET | `/metrics` | public | 200 |
| POST | `/api/v1/auth/register` | public | 201 |
| POST | `/api/v1/auth/login` | public (5/min) | 200 |
| POST | `/api/v1/auth/refresh` | refresh token | 200 |
| GET | `/api/v1/auth/me` | connecté | 200 |
| GET | `/api/v1/doctors/` | public | 200 |
| GET | `/api/v1/doctors/<id>` | public | 200 |
| GET | `/api/v1/doctors/<id>/slots` | public | 200 |
| POST | `/api/v1/doctors/` | admin | 201 |
| PATCH | `/api/v1/doctors/<id>` | admin ou le médecin | 200 |
| DELETE | `/api/v1/doctors/<id>` | admin | 204 |
| GET | `/api/v1/patients/` | admin | 200 |
| GET, PATCH | `/api/v1/patients/<id>` | le patient ou admin | 200 |
| GET | `/api/v1/patients/<id>/appointments` | le patient ou admin | 200 |
| GET | `/api/v1/slots/` | public | 200 |
| GET | `/api/v1/slots/<id>` | public | 200 |
| POST | `/api/v1/slots/` | médecin ou admin | 201 |
| PATCH, DELETE | `/api/v1/slots/<id>` | médecin propriétaire ou admin | 200 / 204 |
| POST | `/api/v1/appointments/` | patient | 201 |
| GET | `/api/v1/appointments/` | connecté (filtré selon le rôle) | 200 |
| GET | `/api/v1/appointments/<id>` | patient ou médecin concerné, admin | 200 |
| PATCH | `/api/v1/appointments/<id>` (`{"status":"cancelled"}`) | patient ou médecin concerné, admin | 200 |

**Collections** : `?page=1&per_page=10` (max 100) → `{"items": [...], "meta": {"page", "per_page", "pages", "total"}}`.
Filtres et tris : `/doctors/?specialty=&q=&sort=-name`, `/slots/?doctor_id=&available=true&date_from=&date_to=&sort=-start_time`, `/appointments/?status=cancelled&sort=start_time`.

**Erreurs** (format unique pour toute l'API) :

```json
{"error": {"status": 409, "code": "slot_already_booked", "message": "Ce creneau est deja reserve.", "details": null, "request_id": "..."}}
```

---

## Architecture

```
sante-api/
├── app/
│   ├── __init__.py          fabrique create_app()                         (TP 3)
│   ├── config.py            Dev / Test / Prod, secrets via os.environ     (TP 3, 5, 6)
│   ├── extensions.py        db, migrate, jwt, cors, limiter               (TP 5, 6, 12)
│   ├── errors.py            format d'erreur unique + handlers globaux     (TP 8)
│   ├── logging_config.py    logs horodatés                                (TP 8)
│   ├── security.py          en-têtes, request id, logs, /metrics          (TP 12)
│   ├── permissions.py       current_user + @roles_required                (TP 6)
│   ├── docs.py              OpenAPI depuis Marshmallow + Swagger UI       (TP 10)
│   ├── commands.py          flask create-admin                            (TP 6)
│   ├── utils.py             UTC, lecture JSON, pagination                 (TP 7)
│   ├── models/              User, Doctor, Patient, Slot, Appointment      (TP 5)
│   ├── schemas/             validation entrée / sortie / query            (TP 4, 7)
│   ├── services/            logique métier                                (TP 3, 5)
│   └── routes/              blueprints /api/v1                            (TP 3)
├── migrations/              Alembic                                       (TP 5)
├── tests/                   pytest + conftest                             (TP 9)
├── scripts/demo.py          parcours de démonstration
├── docs/CONCEPTION.md       contrat d'API et modèle de données
├── Dockerfile, docker-compose.yml, .dockerignore, wsgi.py                 (TP 11)
├── .github/workflows/       intégration continue                          (bonus)
├── CHECKLIST.md             checklist de mise en production              (TP 12)
├── requirements.txt, .env.example, .flaskenv, run.py, pytest.ini
```

Une route ne fait que trois choses : valider l'entrée avec un schéma, appeler un service, renvoyer le JSON avec un code de statut explicite. Toute règle métier est dans `app/services/`.

## Variables d'environnement

Voir [`.env.example`](.env.example).

| Variable | Rôle | Défaut |
|---|---|---|
| `FLASK_CONFIG` | `dev`, `test` ou `prod` | `dev` (`prod` dans Docker) |
| `SECRET_KEY`, `JWT_SECRET_KEY` | secrets (obligatoires en prod) | valeurs de dev refusées en prod |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///sante.db` |
| `CORS_ORIGINS` | origines autorisées, séparées par des virgules | `http://localhost:3000` |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | durée des jetons | 15 min, 7 jours |
| `RATELIMIT_DEFAULT`, `RATELIMIT_STORAGE_URI` | limite globale et stockage | `200 per hour`, `memory://` |