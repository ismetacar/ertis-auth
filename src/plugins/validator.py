from functools import wraps
from jsonschema import ValidationError, validate

from src.utils.errors import BlupointError


def validated(schema):
    def decorator(f):
        @wraps(f)
        async def validate_payload_by_schema(request, *args, **kwargs):
            try:
                payload = request.json
                validate(payload, schema)
            except ValidationError as e:
                raise BlupointError(
                    err_code="errors.validationError",
                    err_msg=str(e.message),
                    status_code=400,
                    context={
                        'required': e.schema.get('required', []),
                        'properties': e.schema.get('properties', {})
                    }
                )
            response = await f(request, *args, **kwargs)
            return response

        return validate_payload_by_schema

    return decorator
