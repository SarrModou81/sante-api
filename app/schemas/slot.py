from marshmallow import Schema, ValidationError, fields, post_load, validate, validates_schema

from app.schemas.common import PaginationQuerySchema
from app.schemas.doctor import DoctorSummarySchema
from app.utils import to_utc_naive


class SlotSchema(Schema):
    id = fields.Int(dump_only=True)
    doctor_id = fields.Int(dump_only=True)
    start_time = fields.DateTime(dump_only=True)
    end_time = fields.DateTime(dump_only=True)
    duration_minutes = fields.Int(dump_only=True)
    is_available = fields.Bool(dump_only=True)
    doctor = fields.Nested(DoctorSummarySchema, dump_only=True)


class _SlotWindowSchema(Schema):
    @post_load
    def normalize(self, data, **kwargs):
        # toutes les dates sont stockees en UTC sans fuseau
        for key in ("start_time", "end_time"):
            if key in data:
                data[key] = to_utc_naive(data[key])
        return data


class SlotCreateSchema(_SlotWindowSchema):
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(required=True)
    doctor_id = fields.Int()  # obligatoire seulement pour un admin (verifie dans le service)


class SlotUpdateSchema(_SlotWindowSchema):
    start_time = fields.DateTime()
    end_time = fields.DateTime()

    @validates_schema
    def not_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("Au moins un champ doit etre fourni.")


class SlotQuerySchema(PaginationQuerySchema):
    doctor_id = fields.Int()
    available = fields.Bool()
    date_from = fields.DateTime()
    date_to = fields.DateTime()
    sort = fields.Str(load_default="start_time", validate=validate.OneOf(["start_time", "-start_time"]))

    @post_load
    def normalize(self, data, **kwargs):
        for key in ("date_from", "date_to"):
            if key in data:
                data[key] = to_utc_naive(data[key])
        return data