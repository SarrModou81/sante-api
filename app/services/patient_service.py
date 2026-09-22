from app.errors import Forbidden, NotFound
from app.extensions import db
from app.models import Patient, Role
from app.utils import paginate

SORTS = {"name": Patient.name.asc(), "-name": Patient.name.desc()}


def list_patients(page=1, per_page=10, q=None, sort="name"):
    query = Patient.query
    if q:
        query = query.filter(Patient.name.ilike(f"%{q}%"))
    return paginate(query.order_by(SORTS[sort], Patient.id), page, per_page)


def get_patient(patient_id, actor):
    """Un patient ne voit que son propre profil ; l'admin voit tout."""
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        raise NotFound("Patient introuvable.", code="patient_not_found")
    if actor.role != Role.ADMIN and patient.user_id != actor.id:
        raise Forbidden("Vous ne pouvez consulter que votre propre profil.")
    return patient


def update_patient(patient_id, data, actor):
    patient = get_patient(patient_id, actor)
    for key, value in data.items():
        setattr(patient, key, value)
    db.session.commit()
    return patient