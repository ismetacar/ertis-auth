from slugify import slugify

from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id

NON_UPDATABLE_FIELDS = [
    '_id', 'slug', 'membership_id'
]

PERMISSION_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'string',
    'enum': [
        '*',
        'users.*',
        'roles.*',
        'user_types.*',
        'applications.*',
        'users.read',
        'users.create',
        'users.update',
        'users.delete',
        'roles.read',
        'roles.create',
        'roles.update',
        'roles.delete',
        'applications.read',
        'applications.create',
        'applications.update',
        'applications.delete',
        'user_types.read',
        'user_types.create',
        'user_types.update',
        'user_types.delete',

    ]
}

ROLE_CRETE_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'name': {
            'type': 'string'
        },
        'permissions': {
            'type': 'array',
            'items': PERMISSION_SCHEMA
        },

    }
}


def generate_slug(role):
    role['slug'] = slugify(role['name'])
    return role


async def check_slug_conflict(db, role):
    existing_role = await db.roles.find_one({
        'slug': role['slug'],
        'membership_id': role['membership_id']
    })

    if existing_role:
        raise ErtisError(
            err_code="errors.roleSlugAlreadyUsing",
            err_msg="Role slug already using",
            status_code=409
        )

    return role


async def find_role(db, role_id, membership_id):
    role = await db.roles.find_one({
        '_id': maybe_object_id(role_id),
        'membership_id': membership_id
    })

    if not role:
        raise ErtisError(
            err_msg="Role not found by given _id: <{}> in membership".format(role_id),
            err_code="errors.roleNotFoundError",
            status_code=404
        )

    return role


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body


async def update_role_with_body(db, role_id, membership_id, body):
    try:
        await db.roles.update_one(
            {
                '_id': maybe_object_id(role_id),
                'membership_id': membership_id
            },
            {
                '$set': body
            }
        )
    except Exception as e:
        raise ErtisError(
            err_code="errors.errorOccurredWhileUpdatingRole",
            err_msg="An error occurred while updating role with provided body",
            status_code=500,
            context={
                'provided_body': body
            },
            reason=str(e)
        )

    role = await find_role(db, role_id, membership_id)
    return role


async def remove_role(db, role_id, membership_id):
    try:
        await db.rpşes.delete_one({
            '_id': maybe_object_id(role_id),
            'membership_id': membership_id
        })
    except Exception as e:
        raise ErtisError(
            err_msg="An error occurred while deleting role",
            err_code="errors.errorOccurdedWhileDeletingRole",
            status_code=500,
            context={
                'role_id': role_id
            },
            reason=str(e)
        )
