from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user

from app.models import Role
from app.permissions import roles_required
from app.schemas.appointment import (AppointmentCreateSchema, AppointmentQuerySchema,
                                     AppointmentSchema, AppointmentUpdateSchema)
from app.schemas.common import paginated_response
from app.services import appointment_service
from app.utils import get_json_body

appointments_bp = Blueprint("appointments", __name__, url_prefix="/api/v1/appointments")

appointment_schema = AppointmentSchema()


@appointments_bp.post("/")
@roles_required(Role.PATIENT)
def book():
    """Reserver un creneau (patient)
    ---
    tags: [Appointments]
    security: [{bearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/AppointmentCreate'}
          example: {slot_id: 1, reason: Douleurs thoraciques}
    responses:
      201:
        description: Rendez-vous cree
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Appointment'}
      401: {description: Jeton manquant}
      403: {description: Reserve aux patients}
      404: {description: Creneau introuvable}
      409:
        description: Creneau deja reserve ou deja passe
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Error'}
      422: {description: Donnees invalides}
    """
    data = AppointmentCreateSchema().load(get_json_body())
    appointment = appointment_service.book_appointment(data, current_user)
    return jsonify(appointment_schema.dump(appointment)), 201


@appointments_bp.get("/")
@roles_required(Role.PATIENT, Role.DOCTOR, Role.ADMIN)
def list_appointments():
    """Mes rendez-vous (patient : les siens ; medecin : les siens avec les patients ; admin : tous)
    ---
    tags: [Appointments]
    security: [{bearerAuth: []}]
    parameters:
      - {in: query, name: page, schema: {type: integer, default: 1}}
      - {in: query, name: per_page, schema: {type: integer, default: 10}}
      - {in: query, name: status, schema: {type: string, enum: [booked, cancelled]}}
      - {in: query, name: sort, schema: {type: string, enum: [start_time, -start_time]}}
    responses:
      200:
        description: Collection paginee
        content:
          application/json:
            schema:
              type: object
              properties:
                items: {type: array, items: {$ref: '#/components/schemas/Appointment'}}
                meta: {$ref: '#/components/schemas/PaginationMeta'}
      401: {description: Jeton manquant}
    """
    args = AppointmentQuerySchema().load(request.args)
    pagination = appointment_service.list_appointments(current_user, **args)
    return jsonify(paginated_response(pagination, appointment_schema)), 200


@appointments_bp.get("/<int:appointment_id>")
@roles_required(Role.PATIENT, Role.DOCTOR, Role.ADMIN)
def get_appointment(appointment_id):
    """Detail d'un rendez-vous (patient ou medecin concerne, ou admin)
    ---
    tags: [Appointments]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: appointment_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: Rendez-vous
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Appointment'}
      403: {description: Rendez-vous d'un autre utilisateur}
      404: {description: Rendez-vous introuvable}
    """
    appointment = appointment_service.get_appointment(appointment_id, current_user)
    return jsonify(appointment_schema.dump(appointment)), 200


@appointments_bp.patch("/<int:appointment_id>")
@roles_required(Role.PATIENT, Role.DOCTOR, Role.ADMIN)
def cancel(appointment_id):
    """Annuler un rendez-vous (jusqu'a 24 h avant)
    ---
    tags: [Appointments]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: appointment_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/AppointmentUpdate'}
          example: {status: cancelled}
    responses:
      200: {description: Rendez-vous annule, creneau libere}
      403: {description: Rendez-vous d'un autre utilisateur}
      404: {description: Rendez-vous introuvable}
      409: {description: Deja annule, ou moins de 24 h avant le rendez-vous}
      422: {description: Statut invalide}
    """
    AppointmentUpdateSchema().load(get_json_body())
    appointment = appointment_service.cancel_appointment(appointment_id, current_user)
    return jsonify(appointment_schema.dump(appointment)), 200