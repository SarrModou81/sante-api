from flask import Flask

from app.config import DEV_JWT_SECRET, DEV_SECRET, config_by_name
from app.extensions import cors, db, jwt, limiter, migrate


def create_app(config_name="dev"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    if config_name == "prod" and (app.config["SECRET_KEY"] == DEV_SECRET
                                  or app.config["JWT_SECRET_KEY"] == DEV_JWT_SECRET):
        raise RuntimeError("SECRET_KEY et JWT_SECRET_KEY doivent etre definies en production.")

    from app.logging_config import configure_logging
    configure_logging(app)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    limiter.init_app(app)

    # Imports dans la fabrique : evite les imports circulaires
    from app import models  # noqa: F401  (enregistre les tables pour Alembic)
    from app import permissions  # noqa: F401  (callback JWT -> current_user)
    from app.commands import register_commands
    from app.errors import register_error_handlers, register_jwt_error_handlers
    from app.routes.auth import auth_bp
    from app.routes.doctors import doctors_bp
    from app.routes.health import health_bp
    from app.routes.patients import patients_bp

    for blueprint in (health_bp, auth_bp, doctors_bp, patients_bp):
        app.register_blueprint(blueprint)

    register_error_handlers(app)
    register_jwt_error_handlers(jwt)
    register_commands(app)

    return app