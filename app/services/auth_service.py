from flask_jwt_extended import create_access_token, create_refresh_token

from app.errors import Conflict, Unauthorized
from app.extensions import db
from app.models import Patient, Role, User


def ensure_email_free(email):
    if User.query.filter_by(email=email).first() is not None:
        raise Conflict("Cet email est deja utilise.", code="email_taken")


def register_patient(data):
    """Inscription publique : cree un compte patient et son profil."""
    ensure_email_free(data["email"])
    user = User(email=data["email"], role=Role.PATIENT)
    user.set_password(data["password"])
    user.patient = Patient(name=data["name"], date_of_birth=data["date_of_birth"])
    db.session.add(user)
    db.session.commit()
    return user


def create_admin(email, password):
    """Utilise par la commande CLI `flask create-admin`."""
    email = email.strip().lower()
    ensure_email_free(email)
    user = User(email=email, role=Role.ADMIN)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(email, password):
    user = User.query.filter_by(email=email).first()
    # meme message que l'email existe ou non : on ne revele pas les comptes existants
    if user is None or not user.check_password(password):
        raise Unauthorized("Email ou mot de passe incorrect.", code="invalid_credentials")
    return user


def _claims(user):
    return {"role": user.role}


def issue_tokens(user):
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity, additional_claims=_claims(user)),
        "refresh_token": create_refresh_token(identity=identity, additional_claims=_claims(user)),
        "token_type": "Bearer",
    }


def refresh_access_token(user):
    return {
        "access_token": create_access_token(identity=str(user.id), additional_claims=_claims(user)),
        "token_type": "Bearer",
    }