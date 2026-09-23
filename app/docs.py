from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flasgger import Swagger

from app.schemas.appointment import AppointmentCreateSchema, AppointmentSchema, AppointmentUpdateSchema
from app.schemas.auth import LoginSchema, RegisterSchema, TokenSchema, UserSchema
from app.schemas.common import ErrorSchema, PaginationMetaSchema
from app.schemas.doctor import DoctorCreateSchema, DoctorSchema, DoctorSummarySchema, DoctorUpdateSchema
from app.schemas.patient import PatientSchema, PatientUpdateSchema
from app.schemas.slot import SlotCreateSchema, SlotSchema, SlotUpdateSchema

# Les schemas Marshmallow sont la source de verite : la doc se met a jour avec eux.
COMPONENTS = {
    "Error": ErrorSchema,
    "PaginationMeta": PaginationMetaSchema,
    "Register": RegisterSchema,
    "Login": LoginSchema,
    "Token": TokenSchema,
    "User": UserSchema,
    "Doctor": DoctorSchema,
    "DoctorSummary": DoctorSummarySchema,
    "DoctorCreate": DoctorCreateSchema,
    "DoctorUpdate": DoctorUpdateSchema,
    "Patient": PatientSchema,
    "PatientUpdate": PatientUpdateSchema,
    "Slot": SlotSchema,
    "SlotCreate": SlotCreateSchema,
    "SlotUpdate": SlotUpdateSchema,
    "Appointment": AppointmentSchema,
    "AppointmentCreate": AppointmentCreateSchema,
    "AppointmentUpdate": AppointmentUpdateSchema,
}


def build_template():
    spec = APISpec(
        title="API Sante - Teleconsultation",
        version="1.0.0",
        openapi_version="3.0.3",
        plugins=[MarshmallowPlugin()],
        info={"description": "Prise de rendez-vous medicaux : medecins, patients, creneaux, rendez-vous."},
    )
    for name, schema in COMPONENTS.items():
        spec.components.schema(name, schema=schema)
    spec.components.security_scheme("bearerAuth", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"})
    return spec.to_dict()


def init_docs(app):
    """Swagger UI sur /docs/ (seulement si SWAGGER_ENABLED, donc pas en production)."""
    if not app.config.get("SWAGGER_ENABLED"):
        return
    app.config["SWAGGER"] = {"title": "API Sante", "openapi": "3.0.3", "uiversion": 3}
    config = {
        "headers": [],
        "specs": [{"endpoint": "apispec", "route": "/apispec.json",
                   "rule_filter": lambda rule: True, "model_filter": lambda tag: True}],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/",
    }
    Swagger(app, template=build_template(), config=config)