from datetime import date

from marshmallow import Schema, ValidationError, fields, validate, validates, validates_schema

from app.schemas.common import PaginationQuerySchema


class PatientSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    date_of_birth = fields.Date(dump_only=True)


class PatientUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=120))
    date_of_birth = fields.Date()

    @validates("date_of_birth")
    def validate_birth(self, value, **kwargs):
        if value > date.today():
            raise ValidationError("La date de naissance ne peut pas etre dans le futur.")

    @validates_schema
    def not_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("Au moins un champ doit etre fourni.")


class PatientQuerySchema(PaginationQuerySchema):
    q = fields.Str()
    sort = fields.Str(load_default="name", validate=validate.OneOf(["name", "-name"]))