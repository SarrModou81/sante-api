from marshmallow import Schema, fields, validate

from app.models.appointment import AppointmentStatus
from app.schemas.common import PaginationQuerySchema
from app.schemas.patient import PatientSchema
from app.schemas.slot import SlotSchema


class AppointmentSchema(Schema):
    id = fields.Int(dump_only=True)
    status = fields.Str(dump_only=True)
    reason = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    cancelled_at = fields.DateTime(dump_only=True, allow_none=True)
    slot = fields.Nested(SlotSchema, dump_only=True)
    # le medecin voit les informations du patient avec chaque rendez-vous
    patient = fields.Nested(PatientSchema, dump_only=True)


class AppointmentCreateSchema(Schema):
    slot_id = fields.Int(required=True)
    reason = fields.Str(required=True, validate=validate.Length(min=3, max=500))


class AppointmentUpdateSchema(Schema):
    # seule transition autorisee par l'API : booked -> cancelled
    status = fields.Str(required=True, validate=validate.OneOf([AppointmentStatus.CANCELLED]))


class AppointmentQuerySchema(PaginationQuerySchema):
    status = fields.Str(validate=validate.OneOf(AppointmentStatus.ALL))
    sort = fields.Str(load_default="start_time", validate=validate.OneOf(["start_time", "-start_time"]))