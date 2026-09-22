from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user

from app.models import Role
from app.permissions import roles_required
from app.schemas.common import paginated_response
from app.schemas.slot import SlotCreateSchema, SlotQuerySchema, SlotSchema, SlotUpdateSchema
from app.services import slot_service
from app.utils import get_json_body

slots_bp = Blueprint("slots", __name__, url_prefix="/api/v1/slots")

slot_schema = SlotSchema()


@slots_bp.get("/")
def list_slots():
    """Liste paginee, filtrable et triable des creneaux (publique)
    ---
    tags: [Slots]
    parameters:
      - {in: query, name: page, schema: {type: integer, default: 1}}
      - {in: query, name: per_page, schema: {type: integer, default: 10, maximum: 100}}
      - {in: query, name: doctor_id, schema: {type: integer}}
      - {in: query, name: available, schema: {type: boolean}}
      - {in: query, name: date_from, schema: {type: string, format: date-time}}
      - {in: query, name: date_to, schema: {type: string, format: date-time}}
      - {in: query, name: sort, schema: {type: string, enum: [start_time, -start_time]}}
    responses:
      200:
        description: Collection paginee
        content:
          application/json:
            schema:
              type: object
              properties:
                items: {type: array, items: {$ref: '#/components/schemas/Slot'}}
                meta: {$ref: '#/components/schemas/PaginationMeta'}
      422: {description: Parametre invalide}
    """
    args = SlotQuerySchema().load(request.args)
    pagination = slot_service.list_slots(**args)
    return jsonify(paginated_response(pagination, slot_schema)), 200


@slots_bp.get("/<int:slot_id>")
def get_slot(slot_id):
    """Detail d'un creneau (public)
    ---
    tags: [Slots]
    parameters:
      - {in: path, name: slot_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: Creneau
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Slot'}
      404: {description: Creneau introuvable}
    """
    return jsonify(slot_schema.dump(slot_service.get_slot(slot_id))), 200


@slots_bp.post("/")
@roles_required(Role.DOCTOR, Role.ADMIN)
def create_slot():
    """Creer un creneau (medecin pour lui-meme, admin avec doctor_id)
    ---
    tags: [Slots]
    security: [{bearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/SlotCreate'}
          example: {start_time: '2030-01-15T09:00:00', end_time: '2030-01-15T09:30:00'}
    responses:
      201:
        description: Creneau cree
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Slot'}
      403: {description: Role non autorise}
      409: {description: Chevauchement avec un creneau existant}
      422: {description: start_time >= end_time, duree hors 15-120 min, ou creneau passe}
    """
    data = SlotCreateSchema().load(get_json_body())
    slot = slot_service.create_slot(data, current_user)
    return jsonify(slot_schema.dump(slot)), 201


@slots_bp.patch("/<int:slot_id>")
@roles_required(Role.DOCTOR, Role.ADMIN)
def update_slot(slot_id):
    """Modifier les horaires d'un creneau libre (medecin proprietaire ou admin)
    ---
    tags: [Slots]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: slot_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/SlotUpdate'}
    responses:
      200: {description: Creneau modifie}
      403: {description: Creneau d'un autre medecin}
      404: {description: Creneau introuvable}
      409: {description: Creneau deja reserve ou chevauchement}
      422: {description: Horaires invalides}
    """
    data = SlotUpdateSchema().load(get_json_body())
    slot = slot_service.update_slot(slot_id, data, current_user)
    return jsonify(slot_schema.dump(slot)), 200


@slots_bp.delete("/<int:slot_id>")
@roles_required(Role.DOCTOR, Role.ADMIN)
def delete_slot(slot_id):
    """Supprimer un creneau sans rendez-vous (medecin proprietaire ou admin)
    ---
    tags: [Slots]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: slot_id, required: true, schema: {type: integer}}
    responses:
      204: {description: Creneau supprime}
      403: {description: Creneau d'un autre medecin}
      404: {description: Creneau introuvable}
      409: {description: Creneau lie a des rendez-vous}
    """
    slot_service.delete_slot(slot_id, current_user)
    return "", 204