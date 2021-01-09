import copy
import datetime
from bson import ObjectId
from src.resources.applications.applications import (
    generate_app_secrets,
    pop_non_updatable_fields,
)
from src.resources.generic import query
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import maybe_object_id


class ApplicationService(object):
    def __init__(self, db, role_service):
        self.db = db
        self.role_service = role_service

    async def create_application(self, resource, utilizer, event_service):
        resource['membership_id'] = utilizer['membership_id']
        resource['_id'] = ObjectId()
        resource['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': utilizer.get('username', utilizer.get('name'))
        }

        await self.role_service.get_role_by_slug(resource['role'], utilizer['membership_id'])

        await self._ensure_name_is_unique_in_membership(resource)
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
        return await self._find_application(resource_id, user['membership_id'])

    async def update_application(self, application_id, data, utilizer, event_service):
        resource = await self._find_application(application_id, utilizer['membership_id'])

        provided_body = pop_non_updatable_fields(data)
        _resource = self._check_identicality(resource, provided_body)

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': utilizer.get('username', utilizer.get('name'))
        })

        provided_body['sys'] = resource['sys']
        updated_application = await self._update_application_with_body(
            application_id, utilizer['membership_id'], provided_body
        )

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
        application = await self._find_application(application_id, utilizer['membership_id'])
        await self._remove_application(utilizer['membership_id'], application_id)

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

    async def _ensure_name_is_unique_in_membership(self, application):
        exists_application = await self.db.applications.find_one({
            'name': application['name'],
            'membership_id': application['membership_id']
        })

        if exists_application:
            raise ErtisError(
                err_msg="Application already exists in db with given name: <{}>".format(application['name']),
                err_code="errors.applicationNameAlreadyExists",
                status_code=400
            )

    async def _find_application(self, application_id, membership_id):
        application = await self.db.applications.find_one({
            '_id': maybe_object_id(application_id),
            'membership_id': membership_id
        })

        if not application:
            raise ErtisError(
                err_code="errors.applicationNotFound",
                err_msg="Application was not found by given id: <{}>".format(application_id),
                status_code=404
            )

        return application

    async def _remove_application(self, membership_id, application_id):
        try:
            await self.db.applications.delete_one({
                '_id': maybe_object_id(application_id),
                'membership_id': membership_id
            })
        except Exception as e:
            raise ErtisError(
                err_msg="An error occurred while deleting user",
                err_code="errors.errorOccurredWhileDeletingUser",
                status_code=500,
                context={
                    'platform_id': application_id
                },
                reason=str(e)
            )

    async def _update_application_with_body(self, application_id, membership_id, provided_body):
        try:
            await self.db.applications.update_one(
                {
                    '_id': maybe_object_id(application_id),
                    'membership_id': membership_id
                },
                {
                    '$set': provided_body
                }
            )
        except Exception as e:
            raise ErtisError(
                err_code="errors.errorOccurredWhileUpdatingUser",
                err_msg="An error occurred while updating user with provided body",
                status_code=500,
                context={
                    'provided_body': provided_body
                },
                reason=str(e)
            )

        application = await self._find_application(application_id, membership_id)
        return application

    @staticmethod
    def _check_identicality(resource, provided_body):
        _resource = copy.deepcopy(resource)

        resource.update(provided_body)
        if resource == _resource:
            raise ErtisError(
                err_msg="Identical document error",
                err_code="errors.identicalDocument",
                status_code=409
            )

        return _resource
