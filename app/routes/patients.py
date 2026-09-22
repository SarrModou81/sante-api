from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user

from app.models import Role
from app.permissions import roles_required
from app.schemas.common import paginated_response
from app.schemas.patient import PatientQuerySchema, PatientSchema, PatientUpdateSchema
from app.services import patient_service
from app.utils import get_json_body

patients_bp = Blueprint("patients", __name__, url_prefix="/api/v1/patients")

patient_schema = PatientSchema()


@patients_bp.get("/")
@roles_required(Role.ADMIN)
def list_patients():
    """Liste paginee des patients (admin)
    ---
    tags: [Patients]
    security: [{bearerAuth: []}]
    parameters:
      - {in: query, name: page, schema: {type: integer, default: 1}}
      - {in: query, name: per_page, schema: {type: integer, default: 10}}
      - {in: query, name: q, schema: {type: string}}
      - {in: query, name: sort, schema: {type: string, enum: [name, -name]}}
    responses:
      200: {description: Collection paginee}
      401: {description: Jeton manquant}
      403: {description: Reserve aux administrateurs}
    """
    args = PatientQuerySchema().load(request.args)
    pagination = patient_service.list_patients(**args)
    return jsonify(paginated_response(pagination, patient_schema)), 200


@patients_bp.get("/<int:patient_id>")
@roles_required(Role.ADMIN, Role.PATIENT)
def get_patient(patient_id):
    """Profil d'un patient (le patient lui-meme ou un admin)
    ---
    tags: [Patients]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: patient_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: Patient
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Patient'}
      403: {description: Profil d'un autre patient}
      404: {description: Patient introuvable}
    """
    patient = patient_service.get_patient(patient_id, current_user)
    return jsonify(patient_schema.dump(patient)), 200


@patients_bp.patch("/<int:patient_id>")
@roles_required(Role.ADMIN, Role.PATIENT)
def update_patient(patient_id):
    """Modifier un profil patient (le patient lui-meme ou un admin)
    ---
    tags: [Patients]
    security: [{bearerAuth: []}]
    parameters:
      - {in: path, name: patient_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema: {$ref: '#/components/schemas/PatientUpdate'}
    responses:
      200: {description: Patient modifie}
      403: {description: Profil d'un autre patient}
      422: {description: Donnees invalides}
    """
    data = PatientUpdateSchema().load(get_json_body())
    patient = patient_service.update_patient(patient_id, data, current_user)
    return jsonify(patient_schema.dump(patient)), 200