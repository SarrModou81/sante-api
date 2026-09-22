from marshmallow import EXCLUDE, Schema, fields, validate


class PaginationQuerySchema(Schema):
    """Parametres de pagination communs a toutes les collections (?page=&per_page=)."""

    class Meta:
        unknown = EXCLUDE  # un parametre d'URL inconnu est ignore

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=10, validate=validate.Range(min=1))


class PaginationMetaSchema(Schema):
    page = fields.Int()
    per_page = fields.Int()
    pages = fields.Int()
    total = fields.Int()


class ErrorBodySchema(Schema):
    status = fields.Int()
    code = fields.Str()
    message = fields.Str()
    details = fields.Raw(allow_none=True)
    request_id = fields.Str(allow_none=True)


class ErrorSchema(Schema):
    error = fields.Nested(ErrorBodySchema)


def paginated_response(pagination, schema):
    """Enveloppe standard d'une collection paginee : items + meta."""
    return {
        "items": schema.dump(pagination.items, many=True),
        "meta": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
            "total": pagination.total,
        },
    }