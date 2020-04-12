import datetime

import jwt
import json
import asyncio
from passlib.hash import bcrypt
from jwt import ExpiredSignatureError
from src.resources.generic import ensure_token_is_not_revoked
from src.resources.tokens.tokens import generate_token
from src.resources.users.users import (
    insert_active_tokens,
    update_user_with_token,
    update_user_token_status,
    remove_from_active_tokens,
    update_user_with_refresh_token
)
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import bson_to_json, maybe_object_id


class ErtisBearerTokenService(object):

    def __init__(self, db):
        self.db = db

    async def generate_token(self, settings, membership, payload, event_service):
        membership_id = str(membership['_id'])
        skip_auth = False

        payload['username'] = payload['username'].lower()
        token_generation_parameters = {
            'body': payload,
            'application_secret': settings['application_secret'],
            'token_ttl': membership['token_ttl'],
            'refresh_token_ttl': membership['refresh_token_ttl'],
            'membership_id': membership_id,
            'skip_auth': skip_auth
        }

        #: await all
        result = await asyncio.gather(
            self.craft_token(**token_generation_parameters),
            self.find_user(payload['username'], membership_id)
        )

        await asyncio.gather(
            update_user_with_token(self.db, result[0], result[1]),
            event_service.on_event((Event(**{
                'document': result[0],
                'prior': {},
                'utilizer': result[1],
                'type': 'TokenCreatedEvent',
                'membership_id': membership_id,
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            })))
        )

        await insert_active_tokens(result[1], result[0], membership, self.db)
        return result

    async def refresh_token(self, do_revoke, refreshable_token, settings, event_service):
        revoke_flag = True if do_revoke == 'true' else False

        user = await self.load_user(
            refreshable_token,
            settings['application_secret'],
            settings['verify_token']
        )

        if user['decoded_token']['rf'] is False:
            raise ErtisError(
                err_msg="Provided token is not refreshable",
                err_code="errors.refreshableTokenError",
                status_code=400
            )

        membership = await self.db.memberships.find_one({
            '_id': maybe_object_id(user['membership_id'])
        })

        await ensure_token_is_not_revoked(self.db, refreshable_token)

        refreshed_token = await self._refresh_token(
            refreshable_token,
            user,
            settings['application_secret'],
            membership['token_ttl'],
            membership['refresh_token_ttl']
        )

        tasks = [update_user_with_refresh_token(self.db, refreshed_token, user),
                 event_service.on_event((Event(**{
                     'document': refreshed_token,
                     'prior': {},
                     'utilizer': user,
                     'type': 'TokenRefreshedEvent',
                     'membership_id': user['membership_id'],
                     'sys': {
                         'created_at': datetime.datetime.utcnow()
                     }
                 })))]

        if revoke_flag:
            now = datetime.datetime.utcnow()
            tasks.append(self.db.revoked_tokens.insert_one({
                'token': refreshable_token,
                'refreshable': user['decoded_token']['rf'],
                'revoked_at': now,
                'token_owner': user,
                'expire_date': now + datetime.timedelta(0, membership['refresh_token_ttl'] * 60)
            }))
        await asyncio.gather(*tasks)

        await remove_from_active_tokens(user, refreshable_token, user['decoded_token']['rf'], self.db)
        await insert_active_tokens(user, refreshed_token, membership, self.db)

        return refreshed_token

    async def verify_token(self, token, settings, event_service):
        await ensure_token_is_not_revoked(self.db, token)
        user = await self.validate_token(token, settings['application_secret'], verify=True)

        token_response = {
            'verified': True,
            'refreshable': user['decoded_token'].get('rf'),
            'token': token
        }

        await event_service.on_event(Event(**{
            'document': token_response,
            'prior': {},
            'utilizer': user,
            'type': 'TokenVerifiedEvent',
            'membership_id': user['membership_id'],
            'sys': {
                'created_at': datetime.datetime.utcnow()
            }
        }))

        return token_response

    async def revoke_token(self, token, settings, event_service):
        user = await self.validate_token(token, settings['application_secret'], verify=True)
        membership = await self.db.memberships.find_one({
            '_id': maybe_object_id(user['membership_id'])
        })

        await ensure_token_is_not_revoked(self.db, token)
        now = datetime.datetime.utcnow()
        await self.db.revoked_tokens.insert_one({
            'token': token,
            'refreshable': user['decoded_token']['rf'],
            'revoked_at': now,
            'token_owner': user,
            'expire_date': now + datetime.timedelta(0, membership['refresh_token_ttl'] * 60)
        })

        await remove_from_active_tokens(user, token, user['decoded_token']['rf'], self.db)

        await asyncio.gather(
            update_user_token_status(self.db, user, token, 'revoked'),
            event_service.on_event(Event(**{
                'document': {'token': token},
                'prior': {},
                'utilizer': user,
                'type': 'TokenRevokedEvent',
                'membership_id': user['membership_id'],
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            })))

        return

    async def me(self, user):

        user_role = await self.db.roles.find_one({
            'slug': user['role'],
            'membership_id': user['membership_id']
        })

        user_permissions = user_role.get('permissions', []) if user_role else []
        user['role_permissions'] = user_permissions

        membership = await self.db.memberships.find_one({
            '_id': maybe_object_id(user['membership_id'])
        })

        user['membership'] = membership
        user.pop('membership_id', None)
        user.pop('password', None)
        user.pop('decoded_token', None)
        return user

    async def validate_token(self, token, secret, verify):
        try:
            decoded = jwt.decode(token, key=secret, algorithms='HS256', verify=verify)

        except ExpiredSignatureError as e:
            raise ErtisError(
                status_code=401,
                err_msg="Provided token has expired",
                err_code="errors.tokenExpiredError",
                context={
                    'message': str(e)
                }
            )
        except Exception as e:
            raise ErtisError(
                status_code=401,
                err_msg="Provided token is invalid",
                err_code="errors.tokenIsInvalid",
                context={
                    'e': str(e)
                }
            )

        where = {
            '_id': maybe_object_id(decoded['prn'])
        }

        user = await self.db.users.find_one(where)
        if not user:
            raise ErtisError(
                err_msg="User could not be found with this token",
                err_code="errors.userNotFound",
                status_code=404
            )
        user['decoded_token'] = decoded

        return user

    async def craft_token(self, **kwargs):
        user = await self.find_user(
            kwargs.get('body')['username'],
            kwargs.get('membership_id'),
        )

        if not user.get('status', None) or user['status'] not in ['active', 'warning']:
            raise ErtisError(
                err_msg="User status: <{}> is not valid to generate token".format(user.get('status', None)),
                err_code="errors.userStatusIsNotValid",
                status_code=401
            )

        if not kwargs.get('skip_auth', False):
            if not bcrypt.verify(kwargs.get('body')["password"], user["password"]):
                raise ErtisError(
                    status_code=403,
                    err_code="errors.wrongUsernameOrPassword",
                    err_msg="Password mismatch"
                )

        payload = {
            'prn': str(user['_id']),
        }

        payload = json.loads(json.dumps(payload, default=bson_to_json))
        token = generate_token(
            payload,
            kwargs.get('application_secret'),
            kwargs.get('token_ttl'),
            kwargs.get('refresh_token_ttl')
        )

        return token

    async def load_user(self, token, secret, verify):
        user = await self.validate_token(token, secret, verify)
        return user

    async def find_user(self, username, membership_id):
        user = await self.db.users.find_one({
            "username": username,
            "membership_id": membership_id
        })

        if not user:
            raise ErtisError(
                err_code="errors.UserNotFound",
                err_msg="User not found in db by given username: <{}>".format(username),
                status_code=401
            )

        return user

    async def _refresh_token(self, token, user, secret, token_ttl, refresh_token_ttl):
        await self.validate_token(token, secret, verify=True)
        payload = {
            "prn": str(user["_id"])
        }
        return generate_token(payload, secret, token_ttl, refresh_token_ttl)
