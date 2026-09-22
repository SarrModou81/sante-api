from app.extensions import db


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(80), nullable=False, index=True)

    # eager (joined) : l'email du compte est affiche avec chaque medecin
    user = db.relationship("User", back_populates="doctor", lazy="joined")
    # lazy (select) : les creneaux ne sont charges que si on en a besoin
    slots = db.relationship("Slot", back_populates="doctor", lazy="select",
                            cascade="all, delete-orphan")

    @property
    def email(self):
        return self.user.email

    def __repr__(self):
        return f"<Doctor {self.name} ({self.specialty})>"