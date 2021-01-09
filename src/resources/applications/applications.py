import random
import string

from slugify import slugify

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


def generate_app_secrets(application):
    application['slug'] = slugify(application['name'])
    app_secret = generate_random_string(32)
    application['secret'] = app_secret

    return application


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body
