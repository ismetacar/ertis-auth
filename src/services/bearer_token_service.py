import copy
import datetime

import jwt
import json
import asyncio

from bson import ObjectId
from passlib.hash import bcrypt
from jwt import ExpiredSignatureError
from src.resources.generic import ensure_token_is_not_revoked
from src.resources.tokens.tokens import generate_token
from src.utils.errors import ErtisError
from src.utils.events import Event
from src.utils.json_helpers import bson_to_json, maybe_object_id


class ErtisBearerTokenService(object):

    def __init__(self, db):
        self.db = db

    async def generate_token(self, settings, membership, payload, event_service, **kwargs):
        membership_id = str(membership['_id'])
        skip_auth = False

        payload['username'] = payload['username'].lower()
        token_generation_parameters = {
            'body': payload,
            'application_secret': settings['application_secret'],
            'token_ttl': membership['token_ttl'],
            'refresh_token_ttl': membership['refresh_token_ttl'],
            'membership_id': membership_id,
            'skip_auth': skip_auth,
            **kwargs
        }

        user = await self._find_user(
            payload['username'],
            membership_id
        )

        await self._check_max_token_count(user, membership)
        self._check_user_status(user)

        token = await self._craft_token(user, **token_generation_parameters)

        await asyncio.gather(
            self._update_user_with_token(token, user),
            event_service.on_event((Event(**{
                'document': token,
                'prior': {},
                'utilizer': user,
                'type': 'TokenCreatedEvent',
                'membership_id': membership_id,
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            }))),
            self._insert_active_tokens(user, token, membership)
        )

        return token

    async def refresh_token(self, do_revoke, refreshable_token, settings, event_service):
        revoke_flag = True if do_revoke == 'true' else False

        user = await self._load_user(
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

        tasks = [
            self._update_user_with_token(refreshed_token, user),
            event_service.on_event((Event(**{
                 'document': refreshed_token,
                 'prior': {},
                 'utilizer': user,
                 'type': 'TokenRefreshedEvent',
                 'membership_id': user['membership_id'],
                 'sys': {
                     'created_at': datetime.datetime.utcnow()
                 }
             })))
        ]

        if revoke_flag:
            tasks.append(self.revoke_token(refreshable_token, settings, event_service, user=user))

        tasks.append(self._remove_from_active_tokens(user, refreshable_token, user['decoded_token']['rf']))
        tasks.append(self._insert_active_tokens(user, refreshed_token, membership))

        await asyncio.gather(*tasks)

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

    async def revoke_token(self, token, settings, event_service, user=None):
        if not user:
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

        await self._remove_from_active_tokens(user, token, user['decoded_token']['rf'])

        await asyncio.gather(
            self._update_user_token_status(user, token, 'revoked'),
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

    async def me(self, user):

        user_role = await self.db.roles.find_one({
            'slug': user['role'],
            'membership_id': user['membership_id']
        })

        user_permissions = user_role.get('permissions', []) if user_role else []
        user['role_permissions'] = user_permissions

        user['membership_owner'] = user_role.get('membership_owner')

        membership = await self.db.memberships.find_one({
            '_id': maybe_object_id(user['membership_id'])
        })

        user['membership'] = membership
        user.pop('membership_id', None)
        user.pop('password', None)
        user.pop('decoded_token', None)
        user.pop('role_definition', None)
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

    async def _craft_token(self, user, **kwargs):
        if not kwargs.get('skip_auth', False):
            if not user.get('password'):
                raise ErtisError(
                    err_code="errors.userShouldCreateANewPassword",
                    err_msg="User should create a new password for generating token.",
                    status_code=400
                )

            self._verify_password(kwargs.get('body')["password"], user["password"])

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

    async def _load_user(self, token, secret, verify):
        user = await self.validate_token(token, secret, verify)
        return user

    async def _find_user(self, username, membership_id):
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

    async def _insert_active_tokens(self, user, token_model, membership):
        access_token = token_model['access_token']
        refresh_token = token_model['refresh_token']
        user_id = str(user['_id'])
        membership_id = str(user['membership_id'])

        now = datetime.datetime.utcnow()
        active_access_token_document = {
            '_id': ObjectId(),
            'user_id': user_id,
            'type': 'access',
            'membership_id': membership_id,
            'token': access_token,
            'created_at': now,
            'expire_date': now + datetime.timedelta(0, membership['token_ttl'] * 60)
        }

        active_refresh_token_document = {
            '_id': ObjectId(),
            'user_id': user_id,
            'type': 'refresh',
            'membership_id': membership_id,
            'token': refresh_token,
            'created_at': now,
            'expire_date': now + datetime.timedelta(0, membership['refresh_token_ttl'] * 60)
        }

        await asyncio.gather(
            self.db.active_tokens.insert_one(active_access_token_document),
            self.db.active_tokens.insert_one(active_refresh_token_document)
        )

    async def _update_user_with_token(self, token, user):
        user_token = copy.deepcopy(token)
        user_token['created_at'] = datetime.datetime.utcnow()
        user_token['access_token_status'] = 'active'
        user_token['refresh_token_status'] = 'active'
        await self.db.users.update_one(
            {
                '_id': maybe_object_id(user['_id'])
            },
            {
                '$set': {
                    'token': user_token,
                    'ip_info': user.get('ip_info', {})
                }
            }
        )

    async def _remove_from_active_tokens(self, user, token, rf):
        where = {
            'membership_id': user['membership_id'],
            'user_id': str(user['_id']),
        }

        if rf:
            where['refresh_token'] = token
        else:
            where['access_token'] = token

        await self.db.active_tokens.delete_one(where)

    async def _update_user_token_status(self, user, revoked_token, status):
        token = user.get('token', {})

        for key, val in token.items():
            if val != revoked_token:
                continue

            field_name = key + '_status'
            token[field_name] = status
            await self.db.users.update_one(
                {
                    '_id': maybe_object_id(user['_id']),
                    'membership_id': user['membership_id']
                },
                {
                    '$set': {
                        'token': token,
                        'ip_info': user.get('ip_info', {})
                    }
                }
            )

    @staticmethod
    def _check_user_status(user):
        if not user.get('status', None) or user['status'] not in ['active', 'warning']:
            raise ErtisError(
                err_msg="User status: <{}> is not valid to generate token".format(user.get('status', None)),
                err_code="errors.userStatusIsNotValid",
                status_code=401
            )

    @staticmethod
    def _verify_password(provided_password, password):
        if not bcrypt.verify(provided_password, password):
            raise ErtisError(
                status_code=403,
                err_code="errors.wrongUsernameOrPassword",
                err_msg="Password mismatch"
            )

    async def _check_max_token_count(self, user, membership):
        max_token_count = membership.get("max_token_count", None)
        if max_token_count:
            active_tokens_of_user = await self.db.active_tokens.count_documents({"user_id": str(user["_id"]), "type": "access"})
            if active_tokens_of_user >= max_token_count:
                raise ErtisError(
                    err_msg="Max token count limit exceeded!",
                    err_code="errors.maxTokenCountLimitExceeded",
                    status_code=403
                )