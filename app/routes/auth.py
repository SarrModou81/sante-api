from flask import Blueprint, jsonify
from flask_jwt_extended import current_user, jwt_required

from app.extensions import limiter
from app.schemas.auth import LoginSchema, RegisterSchema, UserSchema
from app.services import auth_service
from app.utils import get_json_body

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

register_schema = RegisterSchema()
login_schema = LoginSchema()
user_schema = UserSchema()


@auth_bp.post("/register")
def register():
    """Inscription d'un patient
    ---
    tags: [Auth]
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/Register'}
          example: {email: awa@example.com, password: motdepasse123, name: Awa Diop, date_of_birth: '1995-04-12'}
    responses:
      201:
        description: Compte patient cree
        content:
          application/json:
            schema: {$ref: '#/components/schemas/User'}
      409:
        description: Email deja utilise
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Error'}
      422:
        description: Donnees invalides
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Error'}
    """
    data = register_schema.load(get_json_body())
    user = auth_service.register_patient(data)
    return jsonify(user_schema.dump(user)), 201


@auth_bp.post("/login")
@limiter.limit("5 per minute")
def login():
    """Connexion : renvoie un jeton d'acces et un jeton de rafraichissement
    ---
    tags: [Auth]
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/Login'}
          example: {email: awa@example.com, password: motdepasse123}
    responses:
      200:
        description: Authentification reussie
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Token'}
      401:
        description: Identifiants invalides
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Error'}
      429:
        description: Trop de tentatives (5 par minute)
    """
    data = login_schema.load(get_json_body())
    user = auth_service.authenticate(data["email"], data["password"])
    return jsonify(auth_service.issue_tokens(user)), 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """Echange un jeton de rafraichissement contre un nouveau jeton d'acces
    ---
    tags: [Auth]
    security: [{bearerAuth: []}]
    description: Envoyer le **refresh_token** dans l'en-tete Authorization.
    responses:
      200:
        description: Nouveau jeton d'acces
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Token'}
      401:
        description: Jeton manquant, invalide ou expire
    """
    return jsonify(auth_service.refresh_access_token(current_user)), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    """Profil de l'utilisateur connecte
    ---
    tags: [Auth]
    security: [{bearerAuth: []}]
    responses:
      200:
        description: Utilisateur courant et son profil (medecin ou patient)
        content:
          application/json:
            schema: {$ref: '#/components/schemas/User'}
      401:
        description: Jeton manquant ou invalide
    """
    return jsonify(user_schema.dump(current_user)), 200