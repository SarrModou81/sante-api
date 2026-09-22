from datetime import datetime, timezone

from flask import request

from app.errors import BadRequest

MAX_PER_PAGE = 100


def utcnow():
    """Date/heure courante en UTC, sans fuseau (format stocke en base)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(value):
    """Convertit une date avec fuseau en UTC sans fuseau ; laisse une date naive telle quelle."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def get_json_body():
    """Lit le corps JSON de la requete ; 400 si absent ou mal forme."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("Le corps de la requete doit etre un objet JSON valide.", code="invalid_json")
    return data


def paginate(query, page, per_page):
    per_page = min(per_page, MAX_PER_PAGE)  # garde-fou
    return query.paginate(page=page, per_page=per_page, error_out=False)