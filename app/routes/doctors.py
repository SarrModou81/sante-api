from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user

from app.models import Role
from app.permissions import roles_required
from app.schemas.common import PaginationQuerySchema, paginated_response
from app.schemas.doctor import DoctorCreateSchema, DoctorQuerySchema, DoctorSchema, DoctorUpdateSchema
from app.schemas.slot import SlotSchema
from app.services import doctor_service, slot_service
from app.utils import get_json_body

doctors_bp = Blueprint("doctors", __name__, url_prefix="/api/v1/doctors")

doctor_schema = DoctorSchema()
slot_schema = SlotSchema()


@doctors_bp.get("/")
def list_doctors():
    """Liste paginee des medecins (publique)
    ---
    tags: [Doctors]
    parameters:
      - {in: query, name: page, schema: {type: integer, default: 1}}
      - {in: query, name: per_page, schema: {type: integer, default: 10, maximum: 100}}
      - {in: query, name: specialty, schema: {type: string}, description: Filtre exact (insensible a la casse)}
      - {in: query, name: q, schema: {type: string}, description: Recherche dans le nom}
      - {in: query, name: sort, schema: {type: string, enum: [name, -name, specialty, -specialty]}}
    responses:
      200:
        description: Collection paginee
        content:
          application/json:
            schema:
              type: object
              properties:
                items: {type: array, items: {$ref: '#/components/schemas/Doctor'}}
                meta: {$ref: '#/components/schemas/PaginationMeta'}
    """
    args = DoctorQuerySchema().load(request.args)
    pagination = doctor_service.list_doctors(**args)
    return jsonify(paginated_response(pagination, doctor_schema)), 200


@doctors_bp.get("/<int:doctor_id>")
def get_doctor(doctor_id):
    """Profil d'un medecin (public)
    ---
    tags: [Doctors]
    parameters:
      - {in: path, name: doctor_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: Medecin
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Doctor'}
      404:
        description: Medecin introuvable
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Error'}
    """
    return jsonify(doctor_schema.dump(doctor_service.get_doctor(doctor_id))), 200

@doctors_bp.get("/<int:doctor_id>/slots")
def doctor_availabilities(doctor_id):
    """Disponibilites d'un medecin : creneaux libres a venir (public)
    ---
    tags: [Doctors]
    parameters:
      - {in: path, name: doctor_id, required: true, schema: {type: integer}}
      - {in: query, name: page, schema: {type: integer, default: 1}}
      - {in: query, name: per_page, schema: {type: integer, default: 10}}
    responses:
      200:
        description: Collection paginee de creneaux
      404:
        description: Medecin introuvable
    """
    args = PaginationQuerySchema().load(request.args)
    pagination = slot_service.list_doctor_availabilities(doctor_id, **args)
    return jsonify(paginated_response(pagination, slot_schema)), 200

@doctors_bp.post("/")
@roles_required(Role.ADMIN)
def create_doctor():
    """Creer un medecin et son compte (admin)
    ---
    tags: [Doctors]
    security: [{bearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/DoctorCreate'}
          example: {email: dr.fall@example.com, password: motdepasse123, name: Dr Moussa Fall, specialty: Cardiologie}
    responses:
      201:
        description: Medecin cree
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Doctor'}
      401: {description: Jeton manquant}
      403: {description: Reserve aux administrateurs}
      409: {description: Email deja utilise}
      422: {description: Donnees invalides}
    """
    data = DoctorCreateSchema().load(get_json_body())
    doctor = doctor_service.create_doctor(data)
    return jsonify(doctor_schema.dump(doctor)), 201


@doctors_bp.patch("/<int:doctor_id>")
@roles_required(Role.ADMIN, Role.DOCTOR)
def update_doctor(doctor_id):
    """Modifier un medecin (admin, ou le medecin lui-meme)
    ---
    tags: [Doctors]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: doctor_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/DoctorUpdate'}
    responses:
      200: {description: Medecin modifie}
      403: {description: Profil d'un autre medecin}
      404: {description: Medecin introuvable}
      422: {description: Donnees invalides}
    """
    data = DoctorUpdateSchema().load(get_json_body())
    doctor = doctor_service.update_doctor(doctor_id, data, current_user)
    return jsonify(doctor_schema.dump(doctor)), 200


@doctors_bp.delete("/<int:doctor_id>")
@roles_required(Role.ADMIN)
def delete_doctor(doctor_id):
    """Supprimer un medecin (admin)
    ---
    tags: [Doctors]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: doctor_id, required: true, schema: {type: integer}}
    responses:
      204: {description: Medecin supprime}
      403: {description: Reserve aux administrateurs}
      404: {description: Medecin introuvable}
      409: {description: Le medecin a des rendez-vous}
    """
    doctor_service.delete_doctor(doctor_id)
    return "", 204