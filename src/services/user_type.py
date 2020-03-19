import copy
import datetime

from bson import ObjectId

from src.resources.user_types.user_types import (
    slugify_name,
    set_additional_parameters_to_false,
    fill_min_max_fields_if_not_given,
    ensure_user_type_not_exists,
    find_user_type,
    update_user_type_with_body,
    disallow_update_fields,
    regenerate_slug_by_name
)
from src.resources.user_types.validation import validate
from src.utils.errors import ErtisError


class UserTypeService(object):
    def __init__(self, db):
        self.db = db

    async def create_user_type(self, resource, user, membership_id):
        resource = slugify_name(resource)
        await ensure_user_type_not_exists(resource['slug'], membership_id, self.db)

        resource['_id'] = ObjectId()
        resource['sys'] = {
            'created_by': user['username'],
            'created_at': datetime.datetime.utcnow()
        }

        resource['membership_id'] = membership_id

        resource = set_additional_parameters_to_false(resource)
        resource = fill_min_max_fields_if_not_given(resource)
        validate(resource)

        await self.db.user_types.insert_one(resource)

        return resource

    async def get_user_type(self, membership_id, user_type_id=None):
        return await find_user_type(membership_id, self.db, user_type_id=user_type_id, raise_exec=False)

    async def update_user_type(self, membership_id, user_type_id, data, user):
        resource = await self.get_user_type(membership_id, user_type_id=user_type_id)

        _resource = copy.deepcopy(resource)
        _resource.update(data)

        if _resource == resource:
            raise ErtisError(
                err_code="errors.identicalDocumentError",
                err_msg="Identical document error",
                status_code=409
            )

        resource = disallow_update_fields(resource, _resource)
        resource = regenerate_slug_by_name(resource, _resource)
        validate(resource)

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': user['username']
        })

        data['sys'] = resource['sys']

        resource = await update_user_type_with_body(self.db, user_type_id, membership_id, data)
        return resource

