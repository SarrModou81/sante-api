from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.schemas.auth import CredentialsSchema
from app.schemas.common import PaginationQuerySchema


class DoctorSummarySchema(Schema):
    """Version courte, imbriquee dans chaque creneau."""

    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    specialty = fields.Str(dump_only=True)


class DoctorSchema(DoctorSummarySchema):
    email = fields.Email(dump_only=True)


class DoctorCreateSchema(CredentialsSchema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    specialty = fields.Str(required=True, validate=validate.Length(min=2, max=80))


class DoctorUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=120))
    specialty = fields.Str(validate=validate.Length(min=2, max=80))

    @validates_schema
    def not_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("Au moins un champ doit etre fourni.")


class DoctorQuerySchema(PaginationQuerySchema):
    specialty = fields.Str()
    q = fields.Str()
    sort = fields.Str(load_default="name",
                      validate=validate.OneOf(["name", "-name", "specialty", "-specialty"]))