import jwt
import copy
import datetime

from bson import ObjectId
from jsonschema import validate, ValidationError

from src.utils import temporal_helpers
from src.utils.errors import ErtisError

CREATE_TOKEN_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'username': {
            'type': 'string'
        },
        'password': {
            'type': 'string'
        }
    },
    'required': [
        'username',
        'password'
    ]
}

REFRESH_TOKEN_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'token': {
            'type': 'string'
        }
    },
    'required': [
        'token'
    ]
}

RESET_PASSWORD_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'email': {
            'type': 'string',
            'format': 'email'
        }
    },
    'required': [
        'email'
    ]
}

SET_PASSWORD_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'email': {
            'type': 'string',
            'format': 'email'
        },
        'password': {
            'type': 'string'
        },
        'reset_token': {
            'type': 'string'
        }
    },
    'required': [
        'email', 'password', 'reset_token'
    ]
}


def validate_credentials_for_bearer_token(body, opt='CREATE'):
    if opt == 'CREATE':
        schema = CREATE_TOKEN_SCHEMA
    else:
        schema = REFRESH_TOKEN_SCHEMA
    try:
        validate(body, schema)
    except ValidationError as e:
        raise ErtisError(
            err_code="errors.validationError",
            err_msg=str(e.message),
            status_code=400,
            context={
                'required': e.schema.get('required', []),
                'properties': e.schema.get('properties', {})
            }
        )


def _get_exp(token_ttl):
    exp_range = datetime.timedelta(minutes=token_ttl)
    return temporal_helpers.to_timestamp(
        (temporal_helpers.utc_now() + exp_range)
    )


def generate_token(payload, secret, token_ttl, refresh_token_ttl):
    payload.update({
        'exp': _get_exp(token_ttl),
        'jti': str(ObjectId()),
        'iat': temporal_helpers.to_timestamp(temporal_helpers.utc_now()),
        'rf': False
    })

    refresh_token_payload = copy.deepcopy(payload)
    refresh_token_payload['exp'] = _get_exp(refresh_token_ttl)
    refresh_token_payload['rf'] = True
    return {
        'access_token': jwt.encode(payload=payload, key=secret, algorithm='HS256').decode('utf-8'),
        'expires_in': token_ttl * 60,
        'refresh_token': jwt.encode(payload=refresh_token_payload, key=secret, algorithm='HS256').decode('utf-8'),
        'token_type': 'bearer',
        'refresh_token_expires_in': refresh_token_ttl * 60,
        'created_at': datetime.datetime.utcnow()
    }
