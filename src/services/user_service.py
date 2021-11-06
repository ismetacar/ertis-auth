import copy
import datetime
from src.resources.generic import query, OperationTypes
from src.resources.users.users import (
    prepare_user_fields,
    pop_critical_user_fields,
    pop_non_updatable_fields,
    validate_user_model_by_user_type
)
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import maybe_object_id


class UserService(object):
    def __init__(self, db, role_service):
        self.db = db
        self.role_service = role_service

    async def create_user(self, resource, membership_id, utilizer, user_type_service, event_service, creator=None):
        await validate_user_model_by_user_type(
            membership_id,
            resource,
            user_type_service,
            operation=OperationTypes.CREATE,
            creator=creator
        )

        resource = prepare_user_fields(resource, membership_id, resource['password'])
        await self._ensure_email_and_username_available(resource)
        _ = await self.role_service.get_role_by_slug(resource["role"], membership_id)

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
        resource = await self._find_user(resource_id, user['membership_id'])
        resource.pop('password', None)
        resource.pop('token', None)
        return resource

    async def update_user(self, resource_id, data, utilizer, user_type_service, event_service):
        membership_id = utilizer['membership_id']
        resource = await self._find_user(resource_id, membership_id)

        provided_data = pop_non_updatable_fields(data)
        await validate_user_model_by_user_type(
            membership_id,
            resource,
            user_type_service,
            operation=OperationTypes.UPDATE
        )

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
            await self.revoke_and_delete_old_active_tokens(_resource)

        resource['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': utilizer.get('username', utilizer.get('name'))
        })

        provided_data['sys'] = resource['sys']

        resource = await self.update_user_with_body(resource_id, utilizer['membership_id'], provided_data)
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

        user = await self._find_user(resource_id, utilizer["membership_id"])
        user['_id'] = str(user['_id'])

        await self._remove_user(resource_id, utilizer['membership_id'])

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

    async def query_users(self, membership_id, where, select, limit, skip, sort):
        users, count = await query(self.db, membership_id, where, select, limit, skip, sort, 'users')

        users = pop_critical_user_fields(users)
        return users, count

    async def _ensure_email_and_username_available(self, body):
        exists_document = await self.db.users.find_one({
            'email': body['email']
        })

        if exists_document:
            raise ErtisError(
                err_msg="Email already exists",
                err_code="errors.emailAlreadyExists",
                status_code=400
            )

        exists_document = await self.db.users.find_one({
            'username': body['username'],
            'membership_id': body['membership_id']
        })

        if exists_document:
            raise ErtisError(
                err_code="errors.usernameAlreadyExistsInMembership",
                err_msg="Username: <{}> already exists in membership: <{}>".format(
                    body['username'],
                    body['membership_id']
                ),
                status_code=400
            )

    async def _find_user(self, user_id, membership_id):
        user = await self.db.users.find_one({
            '_id': maybe_object_id(user_id),
            'membership_id': membership_id
        })

        if not user:
            raise ErtisError(
                err_msg="User not found in db by given _id: <{}>".format(user_id),
                err_code="errors.userNotFound",
                status_code=404
            )

        return user

    async def _remove_user(self, user_id, membership_id):
        try:
            await self.db.users.delete_one({
                '_id': maybe_object_id(user_id),
                'membership_id': membership_id
            })
        except Exception as e:
            raise ErtisError(
                err_msg="An error occurred while deleting user",
                err_code="errors.errorOccurredWhileDeletingUser",
                status_code=500,
                context={
                    'user_id': user_id
                },
                reason=str(e)
            )

    async def update_user_with_body(self, user_id, membership_id, body):
        try:
            await self.db.users.update_one(
                {
                    '_id': maybe_object_id(user_id),
                    'membership_id': membership_id
                },
                {
                    '$set': body
                }
            )
        except Exception as e:
            raise ErtisError(
                err_code="errors.errorOccurredWhileUpdatingUser",
                err_msg="An error occurred while updating user with provided body",
                status_code=500,
                context={
                    'provided_body': body
                },
                reason=str(e)
            )

        user = await self._find_user(user_id, membership_id)
        return user

    async def revoke_and_delete_old_active_tokens(self, user):
        membership = await self.db.memberships.find_one({
            '_id': maybe_object_id(user['membership_id'])
        })

        where = {
            'membership_id': user['membership_id'],
            'user_id': str(user['_id'])
        }

        active_tokens_document = self.db.active_tokens.find(where)
        active_tokens_document = await active_tokens_document.to_list(length=None)

        for active_token in active_tokens_document:
            now = datetime.datetime.utcnow()
            await self.db.revoked_tokens.insert_one({
                'token': active_token['token'],
                'refreshable': True if active_token['type'] == 'refresh' else False,
                'revoked_at': now,
                'user_id': str(user["_id"]),
                'expire_date': now + datetime.timedelta(0, membership['refresh_token_ttl'] * 60)
            })

        await self.db.active_tokens.delete_many(where)
