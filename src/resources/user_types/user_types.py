from slugify import slugify

from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id


DISALLOW_UPDATE_FILEDS = [
    "slug"
]


def slugify_name(resource):
    """
    Generate slug for created user_type resource for debugging and auditee
    Function order 1
    :param resource:
    :return: resource
    """
    #: slugified_name is for table and stream_names
    #: slug is for collector name resolver
    resource['slug'] = slugify(resource['name'])
    return resource


def set_additional_parameters_to_false(resource):
    """
    Set additional properties false for created user type
    :param resource:
    :return: resource
    """
    resource['schema']['additionalProperties'] = False
    return resource


def fill_min_max_fields_if_not_given(resource):
    """
    Auto complete min & max fields to properties of user type
    :param resource:
    :return: resource
    """
    schema = resource.get('schema', {})

    if not schema:
        raise ErtisError(
            err_code="errors.resourceMustContainSchema",
            err_msg="Resource must contain schema.",
            status_code=400,
            context={
                "given_resource": resource
            }
        )

    for prop, keywords in schema.get('properties', {}).items():
        property_type = keywords.get('type')
        if property_type == 'string':
            if 'minLength' not in keywords:
                keywords['minLength'] = 0

            if 'maxLength' not in keywords:
                keywords['maxLength'] = 100

        if property_type in ['integer', 'number']:
            if 'minimum' not in keywords:
                keywords['minimum'] = 0

            if 'maximum' not in keywords:
                keywords['maximum'] = 100

    return resource


async def ensure_user_type_not_exists(slug, membership_id, db):
    """
    Slug is unique property for user type of membership. So check slug on db.
    :param slug:
    :param membership_id:
    :param db:
    """
    exists_record = await db.user_types.find_one({
        'membership_id': membership_id,
        'slug': slug
    })

    if exists_record:
        raise ErtisError(
            err_code="Slug conflict error. Resource already created as same name before",
            err_msg="errors.userTypeAlreadyExists",
            status_code=409
        )


async def find_user_type(membership_id, db, user_type_id=None, raise_exec=True):
    where = {
        'membership_id': membership_id
    }

    if user_type_id:
        where['_id'] = maybe_object_id(user_type_id)

    user_type = await db.user_types.find_one(where)

    if not user_type and raise_exec:
        raise ErtisError(
            err_msg="User type not found in membership: <{}>".format(membership_id),
            err_code="errors.userTypeNotFound",
            status_code=404
        )

    return user_type


async def update_user_type_with_body(db, user_type_id, membership_id, data):
    try:
        await db.user_types.update_one(
            {
                '_id': maybe_object_id(user_type_id),
                'membership_id': membership_id
            },
            {
                '$set': data
            }
        )
    except Exception as e:
        raise ErtisError(
            err_code="errors.errorOccurredWhileUpdatingUserType",
            err_msg="An error occurred while updating user type with provided body",
            status_code=500,
            context={
                'provided_body': data
            },
            reason=str(e)
        )

    user_type = await find_user_type(membership_id, db, user_type_id)
    return user_type


def disallow_update_fields(resource, _resource):
    for field in DISALLOW_UPDATE_FILEDS:
        if resource[field] != _resource[field]:
            raise ErtisError(
                err_msg="{} is not updatable. Because its generated automatically by system".format(field),
                err_code="errors.badRequest",
                status_code=400
            )

    return resource


def regenerate_slug_by_name(resource, _resource):
    if resource['name'] == _resource['name']:
        return resource

    resource = slugify_name(resource)
    return resource
