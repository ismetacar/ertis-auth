import datetime
import asyncio
import json

from src.resources.users.users import (
    hash_user_password,
    generate_password_reset_fields,
    check_expire_date_for_reset_token
)
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import maybe_object_id


class PasswordService(object):
    def __init__(self, db, user_service):
        self.db = db
        self.user_service = user_service

    async def reset_password(self, payload, membership_id, event_service):
        email = payload['email'].lower()

        user = await self._find_user_by_query({'email': email, 'membership_id': membership_id})

        password_reset = generate_password_reset_fields()
        user = await self._set_reset_password_to_user(
            user['_id'], membership_id,
            {
                'reset_password': password_reset,
                'ip_info': user.get('ip_info', {})
            }
        )

        await event_service.on_event(Event(**{
            'document': password_reset,
            'prior': {},
            'utilizer': user,
            'type': 'PasswordResetEvent',
            'membership_id': user['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow()
            }
        }))

        return user

    async def set_password(self, payload, membership_id, event_service):
        password = payload['password']
        reset_token = payload['reset_token']

        user = await self._find_user_by_query({
            'reset_password.reset_token': reset_token,
            'membership_id': membership_id
        })

        await asyncio.gather(
            self._reset_user_password(user, password),
            event_service.on_event(Event(**{
                'document': user,
                'prior': {},
                'utilizer': user,
                'type': 'PasswordResetEvent',
                'membership_id': user['membership_id'],
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            }))
        )

        await self.user_service.revoke_and_delete_old_active_tokens(user)

    async def change_password(self, payload, user, event_service):
        user_id = payload.get('user_id')
        password = payload.get('password')
        password_confirm = payload.get('password_confirm')

        if not (user['role_definition']['membership_owner'] or user_id == str(user['_id'])):
            raise ErtisError(
                err_msg="User cannot change other users password",
                err_code="errors.userCannotChangeOthersPassword",
                status_code=403
            )

        if password != password_confirm:
            raise ErtisError(
                err_code="errors.passwordAndPasswordConfirmDoesNotMatch",
                err_msg="Password and password confirm does not match",
                status_code=400
            )

        hashed_password = hash_user_password(password)
        await asyncio.gather(
            self.user_service.update_user_with_body(
                user_id, user['membership_id'],
                {'password': hashed_password,
                    'ip_info': user.get('ip_info', {})}
            ),
            event_service.on_event(Event(**{
                'document': user,
                'prior': {},
                'utilizer': user,
                'type': 'PasswordChangedEvent',
                'membership_id': user['membership_id'],
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            })),
            self.user_service.revoke_and_delete_old_active_tokens(user),
        )

    async def _set_reset_password_to_user(self, user_id, membership_id, reset_password_model):
        try:
            await self.db.users.update_one(
                {
                    '_id': maybe_object_id(user_id),
                    'membership_id': membership_id
                },
                {
                    '$set': reset_password_model
                }
            )
        except Exception as e:
            raise ErtisError(
                err_code="errors.errorOccurredWhileUpdatingUser",
                err_msg="An error occurred while updating user with provided body",
                status_code=500,
                context={
                    'provided_body': reset_password_model
                },
                reason=str(e)
            )

        user = await self.db.users.find_one({
            '_id': maybe_object_id(user_id),
            'membership_id': membership_id
        })

        if not user:
            raise ErtisError(
                err_msg="User not found in db by given _id: <{}>".format(
                    user_id),
                err_code="errors.userNotFound",
                status_code=404
            )

        return user

    async def _find_user_by_query(self, where):
        users = await self.db.users.find(where).to_list(length=None)
        if not users:
            raise ErtisError(
                err_msg="User not found by given query <{}>".format(
                    json.dumps(where)),
                err_code="errors.userNotFound",
                status_code=404
            )

        return users[0]

    async def _reset_user_password(self, user, password):
        is_expired = check_expire_date_for_reset_token(
            user['reset_password']['expire_date'])

        if is_expired:
            raise ErtisError(
                err_msg="Provided password reset token has expired",
                err_code="errors.passwordResetTokenHasExpired",
                status_code=400
            )

        new_password = hash_user_password(password)

        await self.db.users.update_one(
            {
                '_id': maybe_object_id(user['_id'])
            },
            {
                '$set': {
                    'password': new_password
                },
                '$unset': {
                    'reset_password': 1
                }
            }
        )
