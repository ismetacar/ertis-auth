import datetime
import json

from jsonschema import ValidationError, validate
from passlib import hash

from src.resources.applications.applications import generate_random_string
from src.resources.generic import OperationTypes
from src.utils.errors import ErtisError
from src.utils.json_helpers import bson_to_json

CHANGE_PASSWORD_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'user_id': {
            'type': 'string'
        },
        'password': {
            'type': 'string'
        },
        'password_confirm': {
            'type': 'string'
        }
    },
    'required': [
        'user_id',
        'password',
        'password_confirm'
    ]
}

NON_UPDATABLE_FIELDS = [
    '_id', 'token', 'membership_id', 'providers'
]


def prepare_user_fields(user, membership_id, password, opt='create'):
    should_be_lowercase_fields = ['username', 'email']
    for field in should_be_lowercase_fields:
        if user.get(field):
            user[field] = user.get(field).lower()

    if opt != 'create':
        return user

    user['providers'] = user.get('providers', [])
    user['email_verified'] = user.get('email_verified', False)
    user['membership_id'] = membership_id
    if password:
        user['password'] = hash_user_password(password)

    return user


def hash_user_password(password):
    hashed_password = hash.bcrypt.hash(password)
    return hashed_password


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body


def pop_critical_user_fields(users):
    for user in users:
        user.pop('password', None)
        user.pop('token', None)

    return users


def generate_password_reset_fields():
    reset_token = generate_random_string(32)
    expires_in = 60 * 60

    return {
        'reset_token': reset_token,
        'expires_in': expires_in,
        'expire_date': datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    }


def check_expire_date_for_reset_token(date):
    if date > datetime.datetime.utcnow():
        return False
    return True


async def generate_user_create_schema(membership_id, user_type_service, operation=OperationTypes.CREATE, creator=None):
    user_create_schema = {
        '$schema': 'http://json-schema.org/schema#',
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'username': {
                'type': 'string'
            },
            'password': {
                'type': 'string'
            },
            'email': {
                'type': 'string',
                'format': 'email'
            },
            'firstname': {
                'type': 'string'
            },
            'lastname': {
                'type': 'string'
            },
            'role': {
                'type': 'string'
            },
            'status': {
                'type': 'string',
                'enum': ['active', 'passive', 'blocked', 'warning']
            }
        },
        'required': [
            'username',
            'password',
            'email',
            'firstname',
            'lastname',
            'role',
            'status'
        ]
    }

    if creator == 'ERTIS':
        user_create_schema['properties'].update({
            'membership_id': {
                'type': 'string'
            },
            'providers': {
                'type': 'array'
            },
            'email_verified': {
                'type': 'boolean'
            }
        })

    if operation == OperationTypes.UPDATE:
        user_create_schema['properties'].update({
            'ip_info': {
                'type': 'object'
            },
            'sys': {
                'type': 'object'
            },
            '_id': {
                'type': 'string'
            },
            'token': {
                'type': 'object'
            },
            'membership_id': {
                'type': 'string'
            },
            'providers': {
                'type': 'array'
            },
            'email_verified': {
                'type': 'boolean'
            }
        })

    user_type = await user_type_service.get_user_type(membership_id)
    if not user_type:
        return user_create_schema

    user_create_schema['properties'].update(user_type['schema']['properties'])
    user_create_schema['required'] += user_type['schema']['required'] if operation == OperationTypes.CREATE else []
    user_create_schema['additionalProperties'] = user_type['schema'].get('additionalProperties', False)
    return user_create_schema


async def validate_user_model_by_user_type(membership_id, payload, user_type_service, operation=OperationTypes.CREATE,
                                           creator=None):
    _payload = json.loads(json.dumps(payload, default=bson_to_json))
    schema = await generate_user_create_schema(membership_id, user_type_service, operation=operation, creator=creator)
    try:
        validate(_payload, schema)
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
