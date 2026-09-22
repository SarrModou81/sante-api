# Conception de l'API Santé (téléconsultation)

Réponses écrites aux questions de réflexion des étapes 0 et 1 du projet final.

---

## Question 1 — Choix du sujet

Sujet retenu : **Sujet D — API de santé (prise de rendez-vous médicaux)**.

1. C'est le sujet où les règles métier dépendent du **temps** : un créneau a un début et une fin (durée entre 15 et 120 min, `start_time < end_time`), et une annulation n'est possible que **jusqu'à 24 h avant** le rendez-vous.
2. La règle « un créneau ne peut pas être réservé deux fois » (409) pose un vrai problème de **concurrence** : deux patients peuvent réserver en même temps. Je la règle avec un `UPDATE` conditionnel atomique.
3. Les droits d'accès changent selon le rôle : un patient ne voit que ses rendez-vous, un médecin voit les siens **avec les infos du patient**, et l'admin voit tout. C'est plus riche qu'un simple « connecté / pas connecté ».
4. Le domaine a de vraies relations (User 1-1 Doctor/Patient, Doctor 1-N Slot, Slot 1-N Appointment). On peut donc justifier des choix lazy/eager.
5. Les données de santé sont sensibles, donc la sécurité (JWT, rôles, en-têtes, rate limiting) a un sens concret ici.

---

## Question 2 — Tableau des ressources

Préfixe commun : `/api/v1`. Trois rôles : **patient**, **doctor**, **admin**.

| Ressource | URL de collection | URL d'élément | Méthodes | Succès | Qui ? |
|---|---|---|---|---|---|
| Auth | `/auth/register` | — | POST | 201 | public (crée un **patient**) |
| Auth | `/auth/login` | — | POST | 200 | public (5 req/min) |
| Auth | `/auth/refresh` | — | POST | 200 | refresh token |
| Auth | `/auth/me` | — | GET | 200 | connecté |
| Doctor | `/doctors/` | `/doctors/<id>` | GET | 200 | public |
| Doctor | `/doctors/` | — | POST | 201 | admin |
| Doctor | — | `/doctors/<id>` | PATCH | 200 | admin ou le médecin lui-même |
| Doctor | — | `/doctors/<id>` | DELETE | 204 | admin |
| Doctor (disponibilités) | `/doctors/<id>/slots` | — | GET | 200 | public |
| Patient | `/patients/` | — | GET | 200 | admin |
| Patient | — | `/patients/<id>` | GET, PATCH | 200 | le patient lui-même ou admin |
| Patient (historique) | `/patients/<id>/appointments` | — | GET | 200 | le patient lui-même ou admin |
| Slot | `/slots/` | `/slots/<id>` | GET | 200 | public |
| Slot | `/slots/` | — | POST | 201 | médecin (pour lui) ou admin |
| Slot | — | `/slots/<id>` | PATCH | 200 | médecin propriétaire ou admin |
| Slot | — | `/slots/<id>` | DELETE | 204 | médecin propriétaire ou admin |
| Appointment | `/appointments/` | — | POST | 201 | patient |
| Appointment | `/appointments/` | `/appointments/<id>` | GET | 200 | selon le rôle (voir règles) |
| Appointment | — | `/appointments/<id>` | PATCH `{"status":"cancelled"}` | 200 | patient ou médecin concerné, admin |
| Health | `/health` | — | GET | 200 / 503 | public (hors `/api/v1`) |

**Écarts au CRUD standard (justifiés) :**

- **Pas de `POST /patients`** : un patient est créé par `POST /auth/register`. L'inscription crée d'un coup le compte (email + mot de passe haché) et le profil.
- **`POST /doctors` réservé à l'admin** : on ne peut pas se déclarer médecin soi-même. Le rôle `admin` n'est donné que par la commande `flask create-admin`.
- **Pas de `DELETE /appointments/<id>`** : un rendez-vous n'est jamais supprimé, il est **annulé** avec `PATCH` sur le statut. On garde ainsi l'historique du patient. `PATCH` convient car on modifie une partie de la ressource.
- **Pas de `PUT`** : toutes les modifications sont partielles (`PATCH`), le client n'envoie que les champs qui changent.
- **`/doctors/<id>/slots` et `/patients/<id>/appointments`** sont des sous-collections en lecture seule. Ce sont des raccourcis pour les « disponibilités » et l'« historique » demandés par l'énoncé.
- **`/auth/login` et `/auth/refresh` en POST** : ce sont des actions qui créent un jeton, pas des ressources.

---

## Question 3 — Les trois codes d'erreur les plus fréquents

| Code | Signification | Situation métier concrète |
|---|---|---|
| **409 Conflict** | La requête est valide mais incompatible avec l'état actuel de la ressource | Un patient réserve un créneau **déjà réservé** (`slot_already_booked`), ou annule **moins de 24 h avant** (`cancellation_too_late`), ou un médecin crée un créneau qui **chevauche** un autre (`slot_overlap`) |
| **422 Unprocessable Entity** | JSON bien formé mais données invalides | Créneau avec `start_time >= end_time`, une durée de 10 min ou 3 h, une date de naissance dans le futur, un email invalide |
| **403 Forbidden** | Authentifié mais pas autorisé | Un patient consulte le rendez-vous d'un autre patient, ou un médecin modifie le créneau d'un autre médecin |

Autres codes utilisés : 400 (JSON illisible), 401 (jeton absent, invalide ou expiré), 404 (ressource introuvable), 429 (trop de tentatives de connexion), 500 (erreur interne, sans détail technique), 503 (`/health` quand la base ne répond pas).

---

## Question 4 — Formats JSON uniques

### Réponse d'erreur (identique pour TOUTE l'API)

```json
{
  "error": {
    "status": 409,
    "code": "slot_already_booked",
    "message": "Ce creneau est deja reserve.",
    "details": null,
    "request_id": "0f6b1c9e-6a1d-4c47-9a53-3c1f7f1e2a10"
  }
}
```

- `status` : le code HTTP (répété dans le corps pour les clients qui ne lisent que le JSON)
- `code` : un identifiant **stable** en snake_case, que le client peut tester (`if code == "slot_already_booked"`)
- `message` : un texte lisible par un humain
- `details` : pour une erreur 422, les erreurs **champ par champ** de Marshmallow ; sinon `null`
- `request_id` : le même identifiant se trouve dans les logs et dans l'en-tête `X-Request-ID`, ce qui aide au support

Exemple 422 :

```json
{
  "error": {
    "status": 422,
    "code": "validation_error",
    "message": "Donnees invalides.",
    "details": {"email": ["Not a valid email address."], "password": ["Missing data for required field."]},
    "request_id": "..."
  }
}
```

### Réponse de collection paginée

`GET /api/v1/slots/?doctor_id=1&available=true&page=1&per_page=2&sort=start_time`

```json
{
  "items": [
    {"id": 1, "doctor_id": 1, "start_time": "2030-01-15T09:00:00", "end_time": "2030-01-15T09:30:00",
     "duration_minutes": 30, "is_available": true,
     "doctor": {"id": 1, "name": "Dr Moussa Fall", "specialty": "Cardiologie"}},
    {"id": 2, "doctor_id": 1, "start_time": "2030-01-15T09:30:00", "end_time": "2030-01-15T10:00:00",
     "duration_minutes": 30, "is_available": true,
     "doctor": {"id": 1, "name": "Dr Moussa Fall", "specialty": "Cardiologie"}}
  ],
  "meta": {"page": 1, "per_page": 2, "pages": 3, "total": 6}
}
```

`per_page` est plafonné à 100. Un `page` ou `per_page` inférieur à 1 renvoie une erreur 422.

---

## Question 5 — Modèle de données

```
┌──────────────┐ 1       0..1 ┌──────────────┐
│    users     │──────────────│   doctors    │
│──────────────│              │──────────────│
│ id (PK)      │              │ id (PK)      │
│ email (UQ)   │              │ user_id (FK, UQ) → users.id
│ password_hash│              │ name         │
│ role         │              │ specialty    │
│ created_at   │              └──────┬───────┘
└──────┬───────┘                     │ 1
       │ 1                           │
       │ 0..1                        │ N
┌──────┴───────┐              ┌──────┴───────┐
│   patients   │              │    slots     │
│──────────────│              │──────────────│
│ id (PK)      │              │ id (PK)      │
│ user_id (FK, UQ) → users.id │ doctor_id (FK) → doctors.id
│ name         │              │ start_time   │
│ date_of_birth│              │ end_time     │
└──────┬───────┘              │ is_available │
       │ 1                    └──────┬───────┘
       │                             │ 1
       │ N                           │ N
       │        ┌──────────────┐     │
       └────────│ appointments │─────┘
                │──────────────│
                │ id (PK)      │
                │ patient_id (FK) → patients.id
                │ slot_id (FK) → slots.id
                │ reason       │
                │ status (booked / cancelled)
                │ created_at   │
                │ cancelled_at │
                └──────────────┘
```

**Cardinalités :**

- `User 1 — 0..1 Doctor` et `User 1 — 0..1 Patient` : un compte a **au plus un** profil. `user_id` est `UNIQUE`. L'authentification est commune (table `users`) et les données métier sont séparées.
- `Doctor 1 — N Slot` : un médecin publie plusieurs créneaux.
- `Slot 1 — N Appointment` : un créneau peut avoir **plusieurs** rendez-vous dans le temps (un réservé puis annulé, un autre ensuite), mais **au plus un actif** (`status = booked`). Cette règle est garantie par `is_available` et l'`UPDATE` atomique.
- `Patient 1 — N Appointment` : l'historique du patient.

**Chargement lazy / eager :**

| Relation | Mode | Pourquoi |
|---|---|---|
| `Doctor.user`, `Patient.user` | **eager** (`joined`) | l'email vient de `users` et s'affiche avec chaque médecin ou patient : une jointure évite une requête de plus par ligne (problème N+1) |
| `Slot.doctor` | **eager** (`joined`) | chaque créneau listé affiche son médecin ; sur une page de 100 créneaux, cela évite 100 requêtes |
| `Appointment.slot`, `Appointment.patient` | **eager** (`joined`) | un rendez-vous est toujours renvoyé avec son créneau et son patient (le médecin doit voir les infos patient) |
| `Doctor.slots` | **lazy** (`select`) | un médecin peut avoir des centaines de créneaux ; on ne les charge pas quand on affiche son profil, on passe par `/slots?doctor_id=` paginé |
| `Patient.appointments`, `Slot.appointments` | **lazy** (`select`) | l'historique complet n'est utile que rarement (vérifier avant une suppression, par exemple) ; il est paginé côté API |

Règle suivie : **eager pour les relations « vers un seul objet » toujours affichées, lazy pour les collections qui peuvent grossir.**