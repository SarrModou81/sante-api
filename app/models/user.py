from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.utils import utcnow


class Role:
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    ALL = (PATIENT, DOCTOR, ADMIN)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.PATIENT)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # 1-1 : un utilisateur a au plus un profil medecin OU un profil patient
    doctor = db.relationship("Doctor", back_populates="user", uselist=False,
                             cascade="all, delete-orphan")
    patient = db.relationship("Patient", back_populates="user", uselist=False,
                              cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"