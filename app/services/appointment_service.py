from datetime import timedelta

from sqlalchemy import update

from app.errors import Conflict, Forbidden, NotFound
from app.extensions import db
from app.models import Appointment, AppointmentStatus, Role, Slot
from app.services.patient_service import get_patient
from app.services.slot_service import get_slot
from app.utils import paginate, utcnow

CANCELLATION_DELAY = timedelta(hours=24)

SORTS = {"start_time": Slot.start_time.asc(), "-start_time": Slot.start_time.desc()}


def book_appointment(data, actor):
    """Un patient reserve un creneau libre et a venir."""
    slot = get_slot(data["slot_id"])
    if slot.start_time <= utcnow():
        raise Conflict("Ce creneau est deja passe.", code="slot_in_past")

    # UPDATE conditionnel atomique : deux reservations simultanees ne peuvent
    # pas reussir toutes les deux (une seule ligne passe de True a False).
    result = db.session.execute(
        update(Slot)
        .where(Slot.id == slot.id, Slot.is_available.is_(True))
        .values(is_available=False)
    )
    if result.rowcount == 0:
        db.session.rollback()
        raise Conflict("Ce creneau est deja reserve.", code="slot_already_booked")

    appointment = Appointment(patient_id=actor.patient.id, slot_id=slot.id, reason=data["reason"])
    db.session.add(appointment)
    db.session.commit()
    return appointment


def _check_access(appointment, actor):
    """Patient : ses rendez-vous. Medecin : les rendez-vous de ses creneaux. Admin : tout."""
    if actor.role == Role.ADMIN:
        return
    if actor.role == Role.PATIENT and appointment.patient_id == actor.patient.id:
        return
    if actor.role == Role.DOCTOR and appointment.slot.doctor_id == actor.doctor.id:
        return
    raise Forbidden("Ce rendez-vous ne vous concerne pas.")


def get_appointment(appointment_id, actor):
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None:
        raise NotFound("Rendez-vous introuvable.", code="appointment_not_found")
    _check_access(appointment, actor)
    return appointment


def list_appointments(actor, page=1, per_page=10, status=None, sort="start_time"):
    query = Appointment.query.join(Slot, Appointment.slot_id == Slot.id)
    if actor.role == Role.PATIENT:
        query = query.filter(Appointment.patient_id == actor.patient.id)
    elif actor.role == Role.DOCTOR:
        query = query.filter(Slot.doctor_id == actor.doctor.id)
    if status:
        query = query.filter(Appointment.status == status)
    return paginate(query.order_by(SORTS[sort], Appointment.id), page, per_page)


def list_patient_history(patient_id, actor, page=1, per_page=10, status=None, sort="start_time"):
    """Historique d'un patient : accessible au patient lui-meme et a l'admin."""
    patient = get_patient(patient_id, actor)
    query = Appointment.query.join(Slot, Appointment.slot_id == Slot.id) \
        .filter(Appointment.patient_id == patient.id)
    if status:
        query = query.filter(Appointment.status == status)
    return paginate(query.order_by(SORTS[sort], Appointment.id), page, per_page)


def cancel_appointment(appointment_id, actor):
    """Annulation possible jusqu'a 24 h avant le debut du rendez-vous ; le creneau est libere."""
    appointment = get_appointment(appointment_id, actor)
    if appointment.status == AppointmentStatus.CANCELLED:
        raise Conflict("Ce rendez-vous est deja annule.", code="already_cancelled")
    if appointment.slot.start_time - utcnow() < CANCELLATION_DELAY:
        raise Conflict("Annulation impossible moins de 24 heures avant le rendez-vous.",
                       code="cancellation_too_late")
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = utcnow()
    appointment.slot.is_available = True
    db.session.commit()
    return appointment