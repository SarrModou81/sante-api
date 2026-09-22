from app.errors import Conflict, Forbidden, NotFound, Unprocessable
from app.extensions import db
from app.models import Role, Slot
from app.services.doctor_service import get_doctor
from app.utils import paginate, utcnow

MIN_DURATION_MINUTES = 15
MAX_DURATION_MINUTES = 120

SORTS = {"start_time": Slot.start_time.asc(), "-start_time": Slot.start_time.desc()}


def list_slots(page=1, per_page=10, doctor_id=None, available=None,
               date_from=None, date_to=None, sort="start_time"):
    query = Slot.query
    if doctor_id is not None:
        query = query.filter(Slot.doctor_id == doctor_id)
    if available is not None:
        query = query.filter(Slot.is_available.is_(available))
    if date_from is not None:
        query = query.filter(Slot.start_time >= date_from)
    if date_to is not None:
        query = query.filter(Slot.start_time <= date_to)
    return paginate(query.order_by(SORTS[sort], Slot.id), page, per_page)


def list_doctor_availabilities(doctor_id, page=1, per_page=10):
    """Disponibilites d'un medecin : creneaux libres et a venir."""
    get_doctor(doctor_id)  # 404 si le medecin n'existe pas
    return list_slots(page, per_page, doctor_id=doctor_id, available=True, date_from=utcnow())


def get_slot(slot_id):
    slot = db.session.get(Slot, slot_id)
    if slot is None:
        raise NotFound("Creneau introuvable.", code="slot_not_found")
    return slot


def _check_window(start, end):
    """Regle metier : start < end, duree entre 15 et 120 minutes, creneau dans le futur."""
    if start >= end:
        raise Unprocessable("start_time doit etre anterieur a end_time.", code="invalid_slot_window")
    minutes = (end - start).total_seconds() / 60
    if not MIN_DURATION_MINUTES <= minutes <= MAX_DURATION_MINUTES:
        raise Unprocessable(
            f"La duree d'un creneau doit etre comprise entre {MIN_DURATION_MINUTES} "
            f"et {MAX_DURATION_MINUTES} minutes.",
            code="invalid_slot_duration",
        )
    if start <= utcnow():
        raise Unprocessable("Un creneau doit commencer dans le futur.", code="slot_in_past")


def _check_overlap(doctor_id, start, end, exclude_id=None):
    """Un medecin ne peut pas avoir deux creneaux qui se chevauchent."""
    query = Slot.query.filter(Slot.doctor_id == doctor_id,
                              Slot.start_time < end, Slot.end_time > start)
    if exclude_id is not None:
        query = query.filter(Slot.id != exclude_id)
    if query.first() is not None:
        raise Conflict("Ce creneau chevauche un creneau existant du medecin.", code="slot_overlap")


def _resolve_doctor(actor, doctor_id):
    """Un medecin cree ses propres creneaux ; un admin doit preciser doctor_id."""
    if actor.role == Role.DOCTOR:
        if doctor_id is not None and doctor_id != actor.doctor.id:
            raise Forbidden("Un medecin ne peut creer des creneaux que pour lui-meme.")
        return actor.doctor
    if doctor_id is None:
        raise Unprocessable("doctor_id est obligatoire pour un administrateur.",
                            code="doctor_id_required")
    return get_doctor(doctor_id)


def _check_owner(slot, actor):
    if actor.role == Role.ADMIN:
        return
    if actor.role == Role.DOCTOR and slot.doctor_id == actor.doctor.id:
        return
    raise Forbidden("Ce creneau appartient a un autre medecin.")


def create_slot(data, actor):
    doctor = _resolve_doctor(actor, data.get("doctor_id"))
    _check_window(data["start_time"], data["end_time"])
    _check_overlap(doctor.id, data["start_time"], data["end_time"])
    slot = Slot(doctor_id=doctor.id, start_time=data["start_time"], end_time=data["end_time"])
    db.session.add(slot)
    db.session.commit()
    return slot


def update_slot(slot_id, data, actor):
    slot = get_slot(slot_id)
    _check_owner(slot, actor)
    if not slot.is_available:
        raise Conflict("Un creneau reserve ne peut pas etre modifie.", code="slot_already_booked")
    start = data.get("start_time", slot.start_time)
    end = data.get("end_time", slot.end_time)
    _check_window(start, end)
    _check_overlap(slot.doctor_id, start, end, exclude_id=slot.id)
    slot.start_time, slot.end_time = start, end
    db.session.commit()
    return slot


def delete_slot(slot_id, actor):
    slot = get_slot(slot_id)
    _check_owner(slot, actor)
    if slot.appointments:
        raise Conflict("Ce creneau est lie a des rendez-vous : suppression impossible.",
                       code="slot_has_appointments")
    db.session.delete(slot)
    db.session.commit()