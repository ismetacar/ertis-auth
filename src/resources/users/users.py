import copy
import json

import datetime

from bson import ObjectId
from passlib import hash
from jsonschema import ValidationError, validate
from src.resources.applications.applications import generate_random_string
from src.resources.generic import OperationTypes
from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id, bson_to_json

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


async def find_user_by_query(db, where):
    users = await db.users.find(where).to_list(length=None)
    if not users:
        raise ErtisError(
            err_msg="User not found by given query <{}>".format(json.dumps(where)),
            err_code="errors.userNotFound",
            status_code=404
        )

    return users[0]


async def find_user(db, user_id, membership_id):
    user = await db.users.find_one({
        '_id': maybe_object_id(user_id),
        'membership_id': membership_id
    })

    if not user:
        raise ErtisError(
            err_msg="User not found in db by given _id: <{}>".format(user_id),
            err_code="errors.userNotFound",
            status_code=404
        )

    return user


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


async def ensure_email_and_username_available(db, body):
    exists_document = await db.users.find_one({
        'email': body['email']
    })

    if exists_document:
        raise ErtisError(
            err_msg="Email already exists",
            err_code="errors.emailAlreadyExists",
            status_code=400
        )

    exists_document = await db.users.find_one({
        'username': body['username'],
        'membership_id': body['membership_id']
    })

    if exists_document:
        raise ErtisError(
            err_code="errors.usernameAlreadyExistsInMembership",
            err_msg="Username: <{}> already exists in membership: <{}>".format(body['username'], body['membership_id']),
            status_code=400
        )


def hash_user_password(password):
    hashed_password = hash.bcrypt.hash(password)
    return hashed_password


async def update_user_with_token(db, token, user):
    user_token = copy.deepcopy(token)
    user_token['created_at'] = datetime.datetime.utcnow()
    user_token['access_token_status'] = 'active'
    user_token['refresh_token_status'] = 'active'
    await db.users.update_one(
        {
            '_id': maybe_object_id(user['_id'])
        },
        {
            '$set': {
                'token': user_token,
                'ip_info': user.get('ip_info', {})
            }
        }
    )


async def update_user_token_status(db, user, revoked_token, status):
    token = user.get('token', {})

    for key, val in token.items():
        if val != revoked_token:
            continue

        field_name = key + '_status'
        token[field_name] = status
        await db.users.update_one(
            {
                '_id': maybe_object_id(user['_id']),
                'membership_id': user['membership_id']
            },
            {
                '$set': {
                    'token': token,
                    'ip_info': user.get('ip_info', {})
                }
            }
        )


async def update_user_with_refresh_token(db, token, user):
    user_token = copy.deepcopy(token)
    user_token['created_at'] = datetime.datetime.utcnow()
    user_token['access_token_status'] = 'active'
    user_token['refresh_token_status'] = 'active'

    await db.users.update_one(
        {
            '_id': maybe_object_id(user['_id'])
        },
        {
            '$set': {
                'token': user_token,
                'ip_info': user.get('ip_info', {})
            }
        }
    )


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body


async def update_user_with_body(db, user_id, membership_id, body):
    try:
        await db.users.update_one(
            {
                '_id': maybe_object_id(user_id),
                'membership_id': membership_id
            },
            {
                '$set': body
            }
        )
    except Exception as e:
        raise ErtisError(
            err_code="errors.errorOccurredWhileUpdatingUser",
            err_msg="An error occurred while updating user with provided body",
            status_code=500,
            context={
                'provided_body': body
            },
            reason=str(e)
        )

    user = await find_user(db, user_id, membership_id)
    return user


async def remove_user(db, user_id, membership_id):
    try:
        await db.users.delete_one({
            '_id': maybe_object_id(user_id),
            'membership_id': membership_id
        })
    except Exception as e:
        raise ErtisError(
            err_msg="An error occurred while deleting user",
            err_code="errors.errorOccurdedWhileDeletingUser",
            status_code=500,
            context={
                'user_id': user_id
            },
            reason=str(e)
        )


async def ensure_provided_role_is_exists(db, user, membership_id):
    if not user.get('role'):
        return

    role = await db.roles.find_one({
        'slug': user['role'],
        'membership_id': membership_id
    })

    if not role:
        raise ErtisError(
            err_msg="Provided role: <{}> was not found in membership".format(user['role']),
            err_code="errors.providedRoleWasNotFound",
            status_code=400
        )


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


async def reset_user_password(db, user, password):
    is_expired = check_expire_date_for_reset_token(user['reset_password']['expire_date'])

    if is_expired:
        raise ErtisError(
            err_msg="Provided password reset token has expired",
            err_code="errors.passwordResetTokenHasExpired",
            status_code=400
        )

    new_password = hash_user_password(password)

    await db.users.update_one(
        {
            '_id': maybe_object_id(user['_id'])
        },
        {
            '$set': {
                'password': new_password
            },
            '$unset': {
                'reset_password': 1
            }
        }
    )


async def insert_active_tokens(user, token_model, membership, db):
    access_token = token_model['access_token']
    refresh_token = token_model['refresh_token']
    user_id = str(user['_id'])
    membership_id = str(user['membership_id'])

    now = datetime.datetime.utcnow()
    active_access_token_document = {
        '_id': ObjectId(),
        'user_id': user_id,
        'type': 'access',
        'membership_id': membership_id,
        'token': access_token,
        'created_at': now,
        'expire_date': now + datetime.timedelta(0, membership['token_ttl'] * 60)
    }

    active_refresh_token_document = {
        '_id': ObjectId(),
        'user_id': user_id,
        'type': 'refresh',
        'membership_id': membership_id,
        'token': refresh_token,
        'created_at': now,
        'expire_date': now + datetime.timedelta(0, membership['refresh_token_ttl'] * 60)
    }

    await db.active_tokens.insert_one(active_access_token_document)
    await db.active_tokens.insert_one(active_refresh_token_document)


async def revoke_and_delete_old_active_tokens(user, db):
    membership = await db.memberships.find_one({
        '_id': maybe_object_id(user['membership_id'])
    })

    where = {
        'membership_id': user['membership_id'],
        'user_id': str(user['_id'])
    }

    active_tokens_document = db.active_tokens.find(where)
    active_tokens_document = await active_tokens_document.to_list(length=None)

    for active_token in active_tokens_document:
        now = datetime.datetime.utcnow()
        await db.revoked_tokens.insert_one({
            'token': active_token['token'],
            'refreshable': True if active_token['type'] == 'refresh' else False,
            'revoked_at': now,
            'token_owner': user,
            'expire_date': now + datetime.timedelta(0, membership['refresh_token_ttl'] * 60)
        })

    await db.active_tokens.delete_many(where)


async def remove_from_active_tokens(user, token, rf, db):
    where = {
        'membership_id': user['membership_id'],
        'user_id': str(user['_id']),
    }

    if rf:
        where['refresh_token'] = token
    else:
        where['access_token'] = token

    await db.active_tokens.delete_one(where)


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


async def validate_user_model_by_user_type(membership_id, payload, user_type_service, operation=OperationTypes.CREATE, creator=None):
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
