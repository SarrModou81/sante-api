from app.extensions import db


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)

    # eager (joined) : l'email du compte est affiche avec chaque patient
    user = db.relationship("User", back_populates="patient", lazy="joined")
    # lazy (select) : l'historique n'est charge que sur demande
    appointments = db.relationship("Appointment", back_populates="patient", lazy="select")

    @property
    def email(self):
        return self.user.email

    def __repr__(self):
        return f"<Patient {self.name}>"