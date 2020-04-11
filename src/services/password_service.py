import datetime
import asyncio
from src.resources.users.users import (
    find_user_by_query,
    hash_user_password,
    reset_user_password,
    update_user_with_body,
    generate_password_reset_fields,
    revoke_and_delete_old_active_tokens
)
from src.utils.errors import ErtisError
from src.utils.events import Event


class PasswordService(object):
    def __init__(self, db):
        self.db = db

    async def reset_password(self, payload, membership_id, event_service):
        email = payload['email'].lower()

        user = await find_user_by_query(self.db, {'email': email, 'membership_id': membership_id})

        password_reset = generate_password_reset_fields()
        user = await update_user_with_body(
            self.db, user['_id'], membership_id,
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
        email = payload['email'].lower()
        password = payload['password']
        reset_token = payload['reset_token']

        user = await find_user_by_query(self.db, {
            'email': email,
            'reset_password.reset_token': reset_token,
            'membership_id': membership_id
        })

        await asyncio.gather(
            reset_user_password(self.db, user, password),
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

        await revoke_and_delete_old_active_tokens(user, self.db)
        return

    async def change_password(self, payload, user, event_service):
        user_id = payload.get('user_id')
        password = payload.get('password')
        password_confirm = payload.get('password_confirm')

        if user_id != str(user['_id']):
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
            update_user_with_body(
                self.db, user_id, user['membership_id'],
                {'password': hashed_password, 'ip_info': user.get('ip_info', {})}
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
            revoke_and_delete_old_active_tokens(user, self.db),
        )

        return
