import copy
import datetime
from bson import ObjectId
from src.resources.generic import query
from src.resources.roles.roles import (
    find_role,
    remove_role,
    generate_slug,
    check_slug_conflict,
    update_role_with_body,
    pop_non_updatable_fields
)
from src.utils.errors import ErtisError


class RoleService(object):
    def __init__(self, db):
        self.db = db

    async def create_role(self, data, user):
        resource = generate_slug(data)
        resource['membership_id'] = user['membership_id']

        role = await check_slug_conflict(self.db, resource)
        role['_id'] = ObjectId()
        role['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': user['username']
        }
        await self.db.roles.insert_one(role)

        return role

    async def get_role(self, resource_id, user):
        return await find_role(self.db, resource_id, user['membership_id'])

    async def update_role(self, resource_id, data, user):
        provided_body = pop_non_updatable_fields(data)

        resource = await find_role(self.db, resource_id, user['membership_id'])
        _resource = copy.deepcopy(resource)
        _resource.update(provided_body)
        if _resource == resource:
            raise ErtisError(
                err_code="errors.identicalDocument",
                err_msg="Identical document error",
                status_code=409
            )

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': user['username']
        })

        provided_body['sys'] = resource['sys']

        return await update_role_with_body(self.db, resource_id, user['membership_id'], provided_body)

    async def delete_role(self, resource_id, user):
        await remove_role(self.db, resource_id, user['membership_id'])

    async def query_roles(self, where, select, limit, skip, sort):
        return await query(self.db, where, select, limit, skip, sort, 'roles')
