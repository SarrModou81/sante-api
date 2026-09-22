from app.extensions import db


class Slot(db.Model):
    __tablename__ = "slots"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True)

    # eager (joined) : chaque creneau liste est affiche avec son medecin (evite N+1)
    doctor = db.relationship("Doctor", back_populates="slots", lazy="joined")
    # lazy (select) : l'historique des rendez-vous du creneau n'est pas toujours utile
    appointments = db.relationship("Appointment", back_populates="slot", lazy="select")

    @property
    def duration_minutes(self):
        return int((self.end_time - self.start_time).total_seconds() // 60)

    def __repr__(self):
        return f"<Slot {self.id} {self.start_time} -> {self.end_time}>"