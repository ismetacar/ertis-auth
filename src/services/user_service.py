import copy
import datetime
from src.resources.generic import query, OperationTypes
from src.resources.users.users import (
    find_user,
    remove_user,
    prepare_user_fields,
    hash_user_password,
    update_user_with_body,
    pop_critical_user_fields,
    pop_non_updatable_fields,
    ensure_provided_role_is_exists,
    ensure_email_and_username_available,
    revoke_and_delete_old_active_tokens,
    validate_user_model_by_user_type)
from src.utils.errors import ErtisError
from src.utils.events import Event


class UserService(object):
    def __init__(self, db):
        self.db = db

    async def create_user(self, resource, membership_id, utilizer, user_type_service, event_service, creator=None):
        await validate_user_model_by_user_type(
            membership_id,
            resource,
            user_type_service,
            operation=OperationTypes.CREATE,
            creator=creator
        )
        resource = prepare_user_fields(resource, membership_id, resource['password'])
        await ensure_email_and_username_available(self.db, resource)
        await ensure_provided_role_is_exists(self.db, resource, membership_id)
        resource['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': utilizer.get('username', utilizer.get('name'))
        }

        await self.db.users.insert_one(resource)
        resource.pop('password', None)

        resource['_id'] = str(resource['_id'])
        await event_service.on_event((Event(**{
            'document': resource,
            'prior': {},
            'utilizer': utilizer,
            'type': 'UserCreatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))

        return resource

    async def get_user(self, resource_id, user):
        resource = await find_user(self.db, resource_id, user['membership_id'])
        resource.pop('password', None)
        resource.pop('token', None)
        return resource

    async def update_user(self, resource_id, data, utilizer, user_type_service, event_service):
        membership_id = utilizer['membership_id']
        resource = await find_user(self.db, resource_id, membership_id)

        provided_data = pop_non_updatable_fields(data)
        await validate_user_model_by_user_type(
            membership_id,
            resource,
            user_type_service,
            operation=OperationTypes.UPDATE
        )
        if data.get('password'):
            if data['password'] != resource['password']:
                data['password'] = hash_user_password(data['password'])
                await revoke_and_delete_old_active_tokens(resource, self.db)
            else:
                data.pop('password', None)

        resource = prepare_user_fields(resource, utilizer['membership_id'], data.get('password'), opt='update')

        _resource = copy.deepcopy(resource)
        _resource.update(provided_data)
        if _resource == resource:
            raise ErtisError(
                err_code="errors.identicalDocument",
                err_msg="Identical document error",
                status_code=409
            )

        if _resource['username'] != resource['username']:
            await revoke_and_delete_old_active_tokens(_resource, self.db)

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': utilizer.get('username', utilizer.get('name'))
        })

        provided_data['sys'] = resource['sys']

        resource = await update_user_with_body(self.db, resource_id, utilizer['membership_id'], provided_data)
        resource.pop('password')

        resource['_id'] = str(resource['_id'])
        _resource['_id'] = str(_resource['_id'])
        await event_service.on_event((Event(**{
            'document': resource,
            'prior': _resource,
            'utilizer': utilizer,
            'type': 'UserUpdatedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))
        return resource

    async def delete_user(self, resource_id, utilizer, event_service):
        if str(utilizer['_id']) == resource_id:
            raise ErtisError(
                err_code="errors.userCannotDeleteHerself",
                err_msg="User can not delete herself",
                status_code=400
            )
        user = await self.get_user(resource_id, utilizer)
        user['_id'] = str(user['_id'])
        await event_service.on_event((Event(**{
            'document': {},
            'prior': user,
            'utilizer': utilizer,
            'type': 'UserDeletedEvent',
            'membership_id': utilizer['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': utilizer.get('username', utilizer.get('name'))
            }
        })))
        await remove_user(self.db, resource_id, utilizer['membership_id'])

    async def query_users(self, membership_id, where, select, limit, skip, sort):
        users, count = await query(self.db, membership_id, where, select, limit, skip, sort, 'users')

        users = pop_critical_user_fields(users)
        return users, count
