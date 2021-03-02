import copy
import datetime
from bson import ObjectId
from src.resources.generic import query
from src.resources.roles.roles import (
    generate_slug,
    pop_non_updatable_fields
)
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import maybe_object_id


class RoleService(object):
    def __init__(self, db):
        self.db = db

    async def create_role(self, data, utilizer, event_service):
        resource = generate_slug(data)
        resource['membership_id'] = utilizer['membership_id']

        role = await self._check_slug_conflict(resource)
        role['_id'] = ObjectId()
        role['membership_owner'] = resource.get('membership_owner', False)
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

    async def get_role(self, role_id, membership_id):
        role = await self._find_role(role_id, membership_id)

        if not role:
            raise ErtisError(
                err_msg="Role not found by given _id: <{}> in membership".format(role_id),
                err_code="errors.roleNotFoundError",
                status_code=404
            )

        return role

    async def get_role_by_slug(self, slug, membership_id):
        role = await self.db.roles.find_one({
            'slug': slug,
            'membership_id': membership_id
        })

        return role

    async def update_role(self, resource_id, data, utilizer, event_service):
        provided_body = pop_non_updatable_fields(data)

        resource = await self.get_role(resource_id, utilizer['membership_id'])
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

        updated_role = await self._update_role_with_body(resource_id, utilizer['membership_id'], provided_body)

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
        role = await self.get_role(resource_id, utilizer["membership_id"])
        await self._remove_role(resource_id, utilizer['membership_id'])

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

    async def _update_role_with_body(self, role_id, membership_id, body):
        try:
            await self.db.roles.update_one(
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

        role = await self._find_role(role_id, membership_id)
        return role

    async def _find_role(self, role_id, membership_id):
        role = await self.db.roles.find_one({
            '_id': maybe_object_id(role_id),
            'membership_id': membership_id
        })

        if not role:
            raise ErtisError(
                err_msg="Role not found by given id: <{}> in membership".format(role_id),
                err_code="errors.roleNotFoundError",
                status_code=404
            )

        return role

    async def _remove_role(self, role_id, membership_id):
        try:
            await self.db.roles.delete_one({
                '_id': maybe_object_id(role_id),
                'membership_id': membership_id
            })
        except Exception as e:
            raise ErtisError(
                err_msg="An error occurred while deleting role",
                err_code="errors.errorOccurredWhileDeletingRole",
                status_code=500,
                context={
                    'role_id': role_id
                },
                reason=str(e)
            )

    async def _check_slug_conflict(self, role):
        existing_role = await self.db.roles.find_one({
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
