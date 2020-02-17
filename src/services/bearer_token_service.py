import copy
import datetime
import hashlib
import json
import jwt
from bson import ObjectId
from jsonschema import validate, ValidationError
from jwt import ExpiredSignatureError

from src.utils.errors import BlupointError
from src.utils import temporal_helpers
from src.utils.json_helpers import bson_to_json, maybe_object_id
from passlib.hash import bcrypt

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
        raise BlupointError(
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
        'refresh_token_expires_in': refresh_token_ttl * 60
    }


class BlupointBearerTokenService(object):

    def __init__(self, db):
        self.db = db

    async def validate_token(self, token, secret, verify):
        try:
            decoded = jwt.decode(token, key=secret, algorithms='HS256', verify=verify)

        except ExpiredSignatureError as e:
            raise BlupointError(
                status_code=401,
                err_msg="Provided token has expired",
                err_code="errors.tokenExpiredError",
                context={
                    'message': str(e)
                }
            )
        except Exception as e:
            raise BlupointError(
                status_code=401,
                err_msg="Provided token is invalid",
                err_code="errors.tokenIsInvalid",
                context={
                    'e': str(e)
                }
            )

        where = {
            '_id': maybe_object_id(decoded['prn'])
        }

        user = await self.db.users.find_one(where)
        if not user:
            raise BlupointError(
                err_msg="User could not be found with this token",
                err_code="errors.userNotFound",
                status_code=404
            )
        user['decoded_token'] = decoded

        return user

    async def craft_token(self, **kwargs):
        user = await self.find_user(
            kwargs.get('body')['username'],
            kwargs.get('membership_id'),
        )

        if not user.get('status', None) or user['status'] not in ['active', 'warning']:
            raise BlupointError(
                err_msg="User status: <{}> is not valid to generate token".format(user.get('status', None)),
                err_code="errors.userStatusIsNotValid",
                status_code=401
            )


        if not kwargs.get('skip_auth', False):

            try:
                if not bcrypt.verify(kwargs.get('body')["password"], user["password"]):
                    raise BlupointError(
                        status_code=403,
                        err_code="errors.wrongUsernameOrPassword",
                        err_msg="Password mismatch"
                    )
            except Exception as ex:
                hashed_password = hashlib.md5(('x1Ya1%sZ1l1e' % kwargs.get('body')["password"]).encode()).hexdigest()

                if user['password'] != hashed_password:
                    raise BlupointError(
                        status_code=403,
                        err_code="errors.wrongUsernameOrPassword",
                        err_msg="Password mismatch"
                    )


        payload = {
            'prn': str(user['_id']),
        }

        payload = json.loads(json.dumps(payload, default=bson_to_json))
        token = generate_token(
            payload,
            kwargs.get('application_secret'),
            kwargs.get('token_ttl'),
            kwargs.get('refresh_token_ttl')
        )

        return token

    async def load_user(self, token, secret, verify):
        user = await self.validate_token(token, secret, verify)
        return user

    async def find_user(self, username, membership_id):
        user = await self.db.users.find_one({
            "username": username,
            "membership_id": membership_id
        })

        if not user:
            raise BlupointError(
                err_code="errors.UserNotFound",
                err_msg="User not found in db by given username: <{}>".format(username),
                status_code=401
            )

        return user

    async def refresh_token(self, token, user, secret, token_ttl, refresh_token_ttl):
        await self.validate_token(token, secret, verify=True)
        payload = {
            "prn": str(user["_id"])
        }
        return generate_token(payload, secret, token_ttl, refresh_token_ttl)
