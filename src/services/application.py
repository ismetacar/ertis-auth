import copy
import datetime
from bson import ObjectId
from src.resources.applications.applications import (
    find_application,
    remove_application,
    generate_app_secrets,
    pop_non_updatable_fields,
    update_application_with_body,
    ensure_name_is_unique_in_membership
)
from src.resources.generic import query
from src.utils.errors import ErtisError


class ApplicationService(object):
    def __init__(self, db):
        self.db = db

    async def create_application(self, resource, user):
        resource['membership_id'] = user['membership_id']
        resource['_id'] = ObjectId()
        resource['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': user['username']
        }

        await ensure_name_is_unique_in_membership(self.db, resource)
        resource = generate_app_secrets(resource)
        await self.db.applications.insert_one(resource)
        return resource

    async def get_application(self, resource_id, user):
        return await find_application(self.db, user['membership_id'], resource_id)

    async def update_application(self, application_id, data, user):
        resource = await find_application(self.db, user['membership_id'], application_id)

        _resource = copy.deepcopy(resource)

        provided_body = pop_non_updatable_fields(data)
        resource.update(provided_body)
        if resource == _resource:
            raise ErtisError(
                err_msg="Identical document error",
                err_code="errors.identicalDocument",
                status_code=409
            )

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': user['username']
        })

        provided_body['sys'] = resource['sys']
        return await update_application_with_body(self.db, application_id, user['membership_id'], provided_body)

    async def delete_application(self, application_id, user):
        await remove_application(self.db, user['membership_id'], application_id)

    async def query_applications(self, membership_id, where, select, limit, skip, sort):
        return await query(self.db, membership_id, where, select, limit, skip, sort, 'applications')
