import random
import string

from slugify import slugify

from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id

APPLICATION_CREATE_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'name': {
            'type': 'string'
        },
        'role': {
            'type': 'string'
        }
    },
    'required': [
        'name'
    ]
}

__CHARS = string.ascii_letters + string.digits

NON_UPDATABLE_FIELDS = [
    '_id', 'secret', 'membership_id', 'slug'
]


def generate_random_string(length=10):
    return ''.join(random.choice(__CHARS) for _ in range(length))


async def ensure_name_is_unique_in_membership(db, application):
    exists_application = await db.applications.find_one({
        'name': application['name'],
        'membership_id': application['membership_id']
    })

    if exists_application:
        raise ErtisError(
            err_msg="Application already exists in db with given name: <{}>".format(application['name']),
            err_code="errors.applicationNameAlreadyExists",
            status_code=400
        )


def generate_app_secrets(application):
    application['slug'] = slugify(application['name'])
    app_secret = generate_random_string(32)
    application['secret'] = app_secret

    return application


async def find_application(db, membership_id, application_id):
    application = await db.applications.find_one({
        '_id': maybe_object_id(application_id),
        'membership_id': membership_id
    })

    if not application:
        raise ErtisError(
            err_code="errors.applicationNotFound",
            err_msg="Application was not found by given id: <{}>".format(application_id),
            status_code=404
        )

    return application


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body


async def update_application_with_body(db, application_id, membership_id, body):
    try:
        await db.applications.update_one(
            {
                '_id': maybe_object_id(application_id),
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

    application = await find_application(db, membership_id, application_id)
    return application


async def remove_application(db, membership_id, application_id):
    try:
        await db.applications.delete_one({
            '_id': maybe_object_id(application_id),
            'membership_id': membership_id
        })
    except Exception as e:
        raise ErtisError(
            err_msg="An error occurred while deleting user",
            err_code="errors.errorOccurredWhileDeletingUser",
            status_code=500,
            context={
                'platform_id': application_id
            },
            reason=str(e)
        )
