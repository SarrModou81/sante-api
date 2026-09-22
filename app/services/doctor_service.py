from app.errors import Conflict, Forbidden, NotFound
from app.extensions import db
from app.models import Appointment, Doctor, Role, Slot, User
from app.services.auth_service import ensure_email_free
from app.utils import paginate

SORTS = {
    "name": Doctor.name.asc(),
    "-name": Doctor.name.desc(),
    "specialty": Doctor.specialty.asc(),
    "-specialty": Doctor.specialty.desc(),
}


def list_doctors(page=1, per_page=10, specialty=None, q=None, sort="name"):
    query = Doctor.query
    if specialty:
        query = query.filter(Doctor.specialty.ilike(specialty))
    if q:
        query = query.filter(Doctor.name.ilike(f"%{q}%"))
    return paginate(query.order_by(SORTS[sort], Doctor.id), page, per_page)


def get_doctor(doctor_id):
    doctor = db.session.get(Doctor, doctor_id)
    if doctor is None:
        raise NotFound("Medecin introuvable.", code="doctor_not_found")
    return doctor


def create_doctor(data):
    """Seul un admin cree un compte medecin (verifie par la route)."""
    ensure_email_free(data["email"])
    user = User(email=data["email"], role=Role.DOCTOR)
    user.set_password(data["password"])
    user.doctor = Doctor(name=data["name"], specialty=data["specialty"])
    db.session.add(user)
    db.session.commit()
    return user.doctor


def update_doctor(doctor_id, data, actor):
    doctor = get_doctor(doctor_id)
    if actor.role != Role.ADMIN and doctor.user_id != actor.id:
        raise Forbidden("Un medecin ne peut modifier que son propre profil.")
    for key, value in data.items():
        setattr(doctor, key, value)
    db.session.commit()
    return doctor


def delete_doctor(doctor_id):
    doctor = get_doctor(doctor_id)
    has_appointments = (
        db.session.query(Appointment.id).join(Slot).filter(Slot.doctor_id == doctor.id).first()
    )
    if has_appointments:
        raise Conflict("Ce medecin a des rendez-vous : suppression impossible.",
                       code="doctor_has_appointments")
    db.session.delete(doctor.user)  # cascade : profil medecin + creneaux
    db.session.commit()