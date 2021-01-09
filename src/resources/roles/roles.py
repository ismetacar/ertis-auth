from slugify import slugify

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


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body
