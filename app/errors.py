from flask import g, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Erreur metier levee par les services, convertie en JSON par le handler global."""

    status = 400
    code = "bad_request"

    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.details = details


class BadRequest(APIError):
    status = 400
    code = "bad_request"


class Unauthorized(APIError):
    status = 401
    code = "unauthorized"


class Forbidden(APIError):
    status = 403
    code = "forbidden"


class NotFound(APIError):
    status = 404
    code = "not_found"


class Conflict(APIError):
    status = 409
    code = "conflict"


class Unprocessable(APIError):
    status = 422
    code = "unprocessable_entity"


def error_response(status, code, message, details=None):
    """Format d'erreur UNIQUE pour toute l'API."""
    body = {
        "error": {
            "status": status,
            "code": code,
            "message": message,
            "details": details,
            "request_id": g.get("request_id"),
        }
    }
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        return error_response(err.status, err.code, err.message, err.details)

    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return error_response(422, "validation_error", "Donnees invalides.", err.messages)

    @app.errorhandler(HTTPException)
    def handle_http(err):
        code = err.name.lower().replace(" ", "_")
        return error_response(err.code, code, err.description)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Erreur non geree")
        return error_response(500, "internal_server_error", "Une erreur interne est survenue.")


def register_jwt_error_handlers(jwt):
    """Les erreurs JWT utilisent le meme format JSON que le reste de l'API."""

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response(401, "missing_token", "Jeton d'authentification manquant.")

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response(401, "invalid_token", "Jeton d'authentification invalide.")

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return error_response(401, "token_expired", "Le jeton a expire.")

    @jwt.user_lookup_error_loader
    def user_not_found(jwt_header, jwt_payload):
        return error_response(401, "user_not_found", "Utilisateur du jeton introuvable.")