from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, limiter

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
@limiter.exempt
def health():
    """Healthcheck profond : verifie reellement la base de donnees.
    ---
    tags: [Health]
    responses:
      200:
        description: API et base de donnees operationnelles
      503:
        description: Base de donnees injoignable
    """
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        current_app.logger.exception("Healthcheck : base de donnees injoignable")
        db.session.rollback()
        return jsonify(status="error", database="unreachable"), 503
    return jsonify(status="ok", database="ok"), 200