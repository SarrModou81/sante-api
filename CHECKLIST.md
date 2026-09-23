# Checklist avant mise en production

## Base (TP 12)

- [x] secrets via variables d'environnement, jamais dans le dépôt (`.env` ignoré, `.env.example` sans vraie valeur)
- [x] `DEBUG = False` en production (`ProdConfig`)
- [x] base PostgreSQL derrière plusieurs workers (`docker-compose.yml`, Gunicorn 4 workers)
- [x] rate limiting actif sur `/auth/login` (5 par minute)
- [x] CORS restreint aux origines connues (`CORS_ORIGINS`, uniquement sur `/api/*`)
- [x] en-têtes de sécurité présents (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- [x] erreurs JSON uniformes, pas de stacktrace exposée (handler global, 500 générique)
- [x] healthcheck `/health` vérifiant la base (`SELECT 1` → 200 / 503)
- [x] suite pytest verte en CI avant tout déploiement (`.github/workflows/tests.yml`, couverture ≥ 70 %)

## Propres au projet (sujet D)

- [x] l'application refuse de démarrer en prod si `SECRET_KEY` ou `JWT_SECRET_KEY` a la valeur de développement
- [x] Swagger UI (`/docs/`) désactivé en production pour ne pas exposer la surface d'attaque
- [x] le rôle `admin` ne s'obtient que par `flask create-admin` (champ `role` refusé à l'inscription)
- [x] la double réservation d'un créneau est impossible même en cas de requêtes simultanées (UPDATE conditionnel atomique)
- [x] toutes les dates sont stockées en UTC (règle des 24 h indépendante du fuseau du serveur)
- [x] `flask db upgrade` reconstruit la base depuis zéro (exécuté au démarrage du conteneur et en CI)
- [x] le conteneur tourne avec un utilisateur non-root et expose un `HEALTHCHECK`
- [x] chaque réponse porte un `X-Request-ID`, repris dans les logs et dans les erreurs JSON

## Risques résiduels et parades

- [ ] **rate limiting et `/metrics` en mémoire, par worker** : avec 4 workers la limite réelle est plus haute → `RATELIMIT_STORAGE_URI=redis://...` et Prometheus pour les métriques
- [ ] **révocation des jetons** : un jeton volé reste valide jusqu'à son expiration (15 min) → liste de révocation (`token_in_blocklist_loader`) stockée dans Redis
- [ ] **HTTPS** : à terminer sur un reverse proxy (Nginx, Traefik) devant Gunicorn, avec `Strict-Transport-Security`