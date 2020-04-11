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
from src.utils.events import Event


class RoleService(object):
    def __init__(self, db):
        self.db = db

    async def create_role(self, data, utilizer, event_service):
        resource = generate_slug(data)
        resource['membership_id'] = utilizer['membership_id']

        role = await check_slug_conflict(self.db, resource)
        role['_id'] = ObjectId()
        role['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': utilizer.get('username', utilizer.get('name'))
        }
        await self.db.roles.insert_one(role)

        role['_id'] = str(role['_id'])
        await event_service.on_event((Event(**{
            'document': role,
            'prior': {},
            'utilizer': utilizer,
            'type': 'RoleCreatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))

        return role

    async def get_role(self, resource_id, user):
        return await find_role(self.db, resource_id, user['membership_id'])

    async def update_role(self, resource_id, data, utilizer, event_service):
        provided_body = pop_non_updatable_fields(data)

        resource = await find_role(self.db, resource_id, utilizer['membership_id'])
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
            'modified_by': utilizer.get('username', utilizer.get('name'))
        })

        provided_body['sys'] = resource['sys']

        updated_role = await update_role_with_body(self.db, resource_id, utilizer['membership_id'], provided_body)

        updated_role['_id'] = str(updated_role['_id'])
        _resource['_id'] = str(_resource['_id'])

        await event_service.on_event((Event(**{
            'document': updated_role,
            'prior': {},
            'utilizer': utilizer,
            'type': 'RoleUpdatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))

        return updated_role

    async def delete_role(self, resource_id, utilizer, event_service):
        role = await self.get_role(resource_id, utilizer)
        await remove_role(self.db, resource_id, utilizer['membership_id'])

        role['_id'] = str(role['_id'])
        await event_service.on_event((Event(**{
            'document': {},
            'prior': role,
            'utilizer': utilizer,
            'type': 'RoleDeletedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))

    async def query_roles(self, membership_id, where, select, limit, skip, sort):
        return await query(self.db, membership_id, where, select, limit, skip, sort, 'roles')
