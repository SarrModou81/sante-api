from datetime import date

from marshmallow import Schema, ValidationError, fields, post_load, validate, validates


class CredentialsSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8, max=128))

    @post_load
    def normalize_email(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        return data


class LoginSchema(CredentialsSchema):
    # au login on ne revele pas la politique de mot de passe : on exige juste un champ non vide
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=1))


class RegisterSchema(CredentialsSchema):
    """Inscription publique : cree toujours un compte PATIENT."""

    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    date_of_birth = fields.Date(required=True)

    @validates("date_of_birth")
    def validate_birth(self, value, **kwargs):
        if value > date.today():
            raise ValidationError("La date de naissance ne peut pas etre dans le futur.")


class TokenSchema(Schema):
    access_token = fields.Str()
    refresh_token = fields.Str()
    token_type = fields.Str()


class UserSchema(Schema):
    """Reponse de /me : le compte + son profil (medecin ou patient)."""

    id = fields.Int()
    email = fields.Email()
    role = fields.Str()
    created_at = fields.DateTime()
    profile = fields.Method("get_profile")

    def get_profile(self, user):
        # import local : evite un import circulaire entre schemas
        from app.schemas.doctor import DoctorSchema
        from app.schemas.patient import PatientSchema

        if user.doctor is not None:
            return DoctorSchema().dump(user.doctor)
        if user.patient is not None:
            return PatientSchema().dump(user.patient)
        return None