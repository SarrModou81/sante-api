import os

from app import create_app

# Point d'entree de Gunicorn : gunicorn "wsgi:app"
app = create_app(os.environ.get("FLASK_CONFIG", "prod"))