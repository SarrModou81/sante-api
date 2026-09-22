from app.extensions import db
from app.utils import utcnow


class AppointmentStatus:
    BOOKED = "booked"
    CANCELLED = "cancelled"
    ALL = (BOOKED, CANCELLED)


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("slots.id"), nullable=False, index=True)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=AppointmentStatus.BOOKED)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # eager (joined) : un rendez-vous est toujours affiche avec son creneau et son patient
    slot = db.relationship("Slot", back_populates="appointments", lazy="joined")
    patient = db.relationship("Patient", back_populates="appointments", lazy="joined")

    def __repr__(self):
        return f"<Appointment {self.id} {self.status}>"