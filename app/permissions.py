from functools import wraps

from flask_jwt_extended import current_user, jwt_required

from app.errors import Forbidden
from app.extensions import db, jwt
from app.models import User


@jwt.user_lookup_loader
def load_user(jwt_header, jwt_payload):
    """Recharge l'utilisateur du jeton : current_user est alors disponible dans les routes."""
    return db.session.get(User, int(jwt_payload["sub"]))


def roles_required(*roles):
    """Exige un jeton valide ET l'un des roles donnes (sinon 401 / 403)."""

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                raise Forbidden("Vous n'avez pas les droits pour cette action.")
            return fn(*args, **kwargs)

        return wrapper

    return decorator