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
from src.resources.roles.roles import get_role_by_id
from src.utils.errors import ErtisError
from src.utils.events import Event


class ApplicationService(object):
    def __init__(self, db):
        self.db = db

    async def create_application(self, resource, utilizer, event_service):
        resource['membership_id'] = utilizer['membership_id']
        resource['_id'] = ObjectId()
        resource['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': utilizer.get('username', utilizer.get('name'))
        }

        await get_role_by_id(self.db, resource['role'], utilizer['membership_id'])

        await ensure_name_is_unique_in_membership(self.db, resource)
        resource = generate_app_secrets(resource)
        await self.db.applications.insert_one(resource)
        await event_service.on_event((Event(**{
            'document': resource,
            'prior': {},
            'utilizer': utilizer,
            'type': 'ApplicationCreatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))
        return resource

    async def get_application(self, resource_id, user):
        return await find_application(self.db, user['membership_id'], resource_id)

    async def update_application(self, application_id, data, utilizer, event_service):
        resource = await find_application(self.db, utilizer['membership_id'], application_id)

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
            'modified_by': utilizer.get('username', utilizer.get('name'))
        })

        provided_body['sys'] = resource['sys']
        updated_application = await update_application_with_body(self.db, application_id, utilizer['membership_id'], provided_body)

        _resource['_id'] = str(_resource['_id'])
        updated_application['_id'] = str(updated_application['_id'])

        await event_service.on_event((Event(**{
            'document': updated_application,
            'prior': _resource,
            'utilizer': utilizer,
            'type': 'ApplicationUpdatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))
        return updated_application

    async def delete_application(self, application_id, utilizer, event_service):
        application = await find_application(self.db, utilizer['membership_id'], application_id)
        await remove_application(self.db, utilizer['membership_id'], application_id)

        application['_id'] = str(application['_id'])
        await event_service.on_event((Event(**{
            'document': {},
            'prior': application,
            'utilizer': utilizer,
            'type': 'ApplicationDeletedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))

    async def query_applications(self, membership_id, where, select, limit, skip, sort):
        return await query(self.db, membership_id, where, select, limit, skip, sort, 'applications')
