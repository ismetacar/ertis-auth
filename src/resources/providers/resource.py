import copy
from functools import reduce

from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id

NON_UPDATABLE_FIELDS = [
    '_id', 'type', 'membership_id', 'slug'
]

CREATE_PROVIDER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "type": {
            "type": "string",
            "enum": ["google", "facebook"]
        },
        "default_role": {
            "type": "string"
        },
        "default_creator_name": {
            "type": "string"
        },
        "mapping": {
            "type": "object"
        }
    },
    "required": ["name", "type", "default_role", "default_creator_name", "mapping"],
    "additionalProperties": False
}


def dot_to_json(a):
    output = {}
    for key, value in a.items():
        path = key.split('.')
        if path[0] == 'json':
            path = path[1:]
        target = reduce(lambda d, k: d.setdefault(k, {}), path[:-1], output)
        target[path[-1]] = value
    return output


class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def get_default_type(_type):
    if _type == 'string':
        return ''
    elif _type == 'number':
        return 0
    elif _type == 'array':
        return 0
    elif _type == 'boolean':
        return False


def prepare_properties(properties):
    obj = {}
    for key, val in properties.items():
        if val['type'] == 'object':
            value = prepare_properties(val['properties'])
        else:
            value = get_default_type(val['type'])

        obj[key] = value

    obj = DotDict(obj)
    return obj


def map_values_by_mapping(mapping, prepared_properties, user):
    _mapping = copy.deepcopy(mapping)
    for key, val in mapping.items():
        if key not in prepared_properties.keys():
            continue
        if isinstance(val, str):
            _mapping[key] = user.get(val, None)
        if isinstance(val, dict):
            _mapping[key] = map_values_by_mapping(val, prepared_properties[key], user)

    prepared_properties.update(_mapping)
    return prepared_properties


async def find_provider(db, membership_id, provider_id):
    provider = await db.providers.find_one({
        '_id': maybe_object_id(provider_id),
        'membership_id': membership_id
    })

    if not provider:
        raise ErtisError(
            err_code="errors.providerNotFound",
            err_msg="Provider was not found by given id: <{}>".format(provider_id),
            status_code=404
        )

    return provider


def pop_non_updatable_fields(body):
    for field in NON_UPDATABLE_FIELDS:
        body.pop(field, None)

    return body


async def update_provider_with_body(db, provider_id, membership_id, body):
    try:
        await db.providers.update_one(
            {
                '_id': maybe_object_id(provider_id),
                'membership_id': membership_id
            },
            {
                '$set': body
            }
        )
    except Exception as e:
        raise ErtisError(
            err_code="errors.errorOccurredWhileUpdatingProvider",
            err_msg="An error occurred while updating provider with provided body",
            status_code=500,
            context={
                'provided_body': body
            },
            reason=str(e)
        )

    provider = await find_provider(db, membership_id, provider_id)
    return provider


async def remove_provider(db, membership_id, provider_id):
    try:
        await db.providers.delete_one({
            '_id': maybe_object_id(provider_id),
            'membership_id': membership_id
        })
    except Exception as e:
        raise ErtisError(
            err_msg="An error occurred while deleting provider",
            err_code="errors.errorOccurredWhileDeletingProvider",
            status_code=500,
            context={
                '_id': provider_id
            },
            reason=str(e)
        )
