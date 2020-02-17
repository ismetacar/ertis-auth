import asyncio
import datetime
import json
import logging

from sanic.response import json

from src.plugins.authorization import authorized, ensure_valid_token_provided, ensure_user_is_permitted
from src.plugins.resolve_ip import resolve_ip
from src.plugins.validator import validated
from src.resources.generic import ensure_token_is_not_revoked, ensure_membership_is_exists
from src.resources.users import (
    update_user_with_token,
    update_user_with_refresh_token,
    generate_password_reset_fields,
    update_user_with_body,
    reset_user_password,
    find_user_by_query,
    CHANGE_PASSWORD_SCHEMA, hash_user_password,
    update_user_token_status, update_active_tokens,
    revoke_and_delete_old_active_tokens,
    pop_revoked_token_from_active_tokens)
from src.services.bearer_token_service import (
    CREATE_TOKEN_SCHEMA,
    REFRESH_TOKEN_SCHEMA,
    RESET_PASSWORD_SCHEMA,
    SET_PASSWORD_SCHEMA
)
from src.utils.errors import BlupointError
from src.utils.events import Event
from src.utils.json_helpers import convert_custom_header_json


def init_token_api(app, settings):
    # region Generate Token
    @app.route('/api/v1/generate-token', methods=['POST'])
    @validated(CREATE_TOKEN_SCHEMA)
    @resolve_ip()
    async def create_token(request, **kwargs):
        body = request.json
        auth_header = request.headers.get('authorization', None)
        membership_id = request.headers.get('x-blupoint-alias', None)

        await ensure_membership_is_exists(app.db, membership_id, user=None)
        skip_auth = False

        if auth_header:
            token = ensure_valid_token_provided(auth_header)
            await ensure_token_is_not_revoked(app.db, token)
            user = await app.bearer_token_service.validate_token(token, settings['application_secret'], verify=True)
            if user['membership_id'] != membership_id:
                raise BlupointError(
                    err_code="errors.userNotPermitted",
                    err_msg="User not permitted in this membership",
                    status_code=401
                )
            await ensure_user_is_permitted(app.db, user, 'users.generate_token')
            skip_auth = True

        body['username'] = body['username'].lower()
        token_generation_parameters = {
            'body': body,
            'application_secret': settings['application_secret'],
            'token_ttl': settings['token_ttl'],
            'refresh_token_ttl': settings['refresh_token_ttl'],
            'membership_id': membership_id,
            'skip_auth': skip_auth
        }

        #: await all
        result = await asyncio.gather(
            app.bearer_token_service.craft_token(**token_generation_parameters),
            app.bearer_token_service.find_user(body['username'], membership_id)
        )

        if kwargs['ip_address']:
            result[1]['ip_info'] = kwargs.get('ip_info', {})

        custom = convert_custom_header_json(request.headers)
        await asyncio.gather(
            update_user_with_token(app.db, result[0], result[1]),
            app.persist_event.on_event((Event(**{
                'document': result[0],
                'user': result[1],
                'type': 'TokenCreatedEvent',
                'username': result[1]['username'],
                'membership_id': membership_id,
                'custom': custom,
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            })))
        )

        await update_active_tokens(result[1], result[0], app.db)

        return json(result[0], 201)

    # endregion

    # region Refresh Token
    @app.route('/api/v1/refresh-token', methods=['POST'])
    @validated(REFRESH_TOKEN_SCHEMA)
    @resolve_ip()
    async def refresh_token(request, **kwargs):
        body = request.json
        refreshable_token = body['token']

        revoke_flag = True if request.args.get('revoke','true').lower() == 'true' else False

        user = await app.bearer_token_service.load_user(
            refreshable_token,
            settings['application_secret'],
            settings['verify_token']
        )

        if user['decoded_token']['rf'] is False:
            raise BlupointError(
                err_msg="Provided token is not refreshable",
                err_code="errors.refreshableTokenError",
                status_code=400
            )

        await ensure_token_is_not_revoked(app.db, refreshable_token)

        refreshed_token = await app.bearer_token_service.refresh_token(
            refreshable_token,
            user,
            settings['application_secret'],
            settings['token_ttl'],
            settings['refresh_token_ttl']
        )

        if kwargs['ip_address']:
            user['ip_info'] = kwargs.get('ip_info', {})

        tasks = [update_user_with_refresh_token(app.db, refreshed_token, user),
                 app.persist_event.on_event((Event(**{
                     'document': refreshed_token,
                     'user': user,
                     'type': 'TokenRefreshedEvent',
                     'username': user['username'],
                     'membership_id': user['membership_id'],
                     'sys': {
                         'created_at': datetime.datetime.utcnow()
                     }
                 })))]

        if revoke_flag:
            tasks.append(app.db.revoked_tokens.insert_one({
                'token': refreshable_token,
                'refreshable': user['decoded_token']['rf'],
                'revoked_at': datetime.datetime.utcnow(),
                'token_owner': user

            }))
        await asyncio.gather(*tasks)

        await pop_revoked_token_from_active_tokens(user, refreshable_token, user['decoded_token']['rf'], app.db)

        await update_active_tokens(user, refreshed_token, app.db)

        return json(refreshed_token)

    # endregion

    # region Verify Token
    @app.route('/api/v1/verify-token', methods=['POST'])
    @validated(REFRESH_TOKEN_SCHEMA)
    @resolve_ip()
    async def verify_token(request, **kwargs):
        body = request.json
        token = body['token']

        await ensure_token_is_not_revoked(app.db, token)
        user = await app.bearer_token_service.validate_token(token, settings['application_secret'], verify=True)

        response_json = {
            'verified': True,
            'refreshable': user['decoded_token'].get('rf'),
            'token': token
        }

        if kwargs['ip_address']:
            user['ip_info'] = kwargs.get('ip_info', {})

        custom = convert_custom_header_json(request.headers)
        await app.persist_event.on_event(Event(**{
            'document': response_json,
            'user': user,
            'type': 'TokenVerifiedEvent',
            'username': user['username'],
            'membership_id': user['membership_id'],
            'custom': custom,
            'sys': {
                'created_at': datetime.datetime.utcnow()
            }
        }))

        return json(response_json)

    # endregion

    # region Revoke Token
    @app.route('/api/v1/revoke-token', methods=['POST'])
    @validated(REFRESH_TOKEN_SCHEMA)
    @resolve_ip()
    async def revoke_token(request, **kwargs):
        body = request.json
        token = body['token']

        user = await app.bearer_token_service.validate_token(token, settings['application_secret'], verify=True)

        if kwargs['ip_address']:
            user['ip_info'] = kwargs.get('ip_info', {})

        await ensure_token_is_not_revoked(app.db, token)
        await app.db.revoked_tokens.insert_one({
            'token': token,
            'refreshable': user['decoded_token']['rf'],
            'revoked_at': datetime.datetime.utcnow(),
            'token_owner': user
        })

        await pop_revoked_token_from_active_tokens(user, token, user['decoded_token']['rf'], app.db)

        custom = convert_custom_header_json(request.headers)
        await asyncio.gather(
            update_user_token_status(app.db, user, token, 'revoked'),
            app.persist_event.on_event(Event(**{
                'document': {'token': token},
                'user': user,
                'type': 'TokenRevokedEvent',
                'username': user['username'],
                'membership_id': user['membership_id'],
                'custom': custom,
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            })))

        return json({}, 204)

    # endregion

    # region Reset Password
    @app.route('/api/v1/reset-password', methods=['POST'])
    @validated(RESET_PASSWORD_SCHEMA)
    @resolve_ip()
    async def reset_password(request, **kwargs):
        membership_id = request.headers.get('x-blupoint-alias', None)

        await ensure_membership_is_exists(app.db, membership_id, user=None)

        body = request.json
        email = body['email'].lower()

        user = await find_user_by_query(app.db, {'email': email, 'membership_id': membership_id})

        if kwargs['ip_address']:
            user['ip_info'] = kwargs.get('ip_info', {})

        password_reset = generate_password_reset_fields()
        user = await update_user_with_body(
            app.db, user['_id'], membership_id,
            {'reset_password': password_reset, 'ip_info': user.get('ip_info', {})}
        )

        custom = convert_custom_header_json(request.headers)
        await app.persist_event.on_event(Event(**{
            'document': password_reset,
            'user': user,
            'type': 'PasswordResetEvent',
            'username': user['username'].lower(),
            'membership_id': user['membership_id'],
            'custom': custom,
            'sys': {
                'created_at': datetime.datetime.utcnow()
            }
        }))

        return json(user['reset_password'], 200)

    # endregion

    # region Set New Password
    @app.route('/api/v1/set-password', methods=['POST'])
    @validated(SET_PASSWORD_SCHEMA)
    @resolve_ip()
    async def set_password(request, **kwargs):
        membership_id = request.headers.get('x-blupoint-alias', None)

        await ensure_membership_is_exists(app.db, membership_id, user=None)
        body = request.json

        email = body['email'].lower()
        password = body['password']
        reset_token = body['reset_token']

        user = await find_user_by_query(app.db, {
            'email': email,
            'reset_password.reset_token': reset_token,
            'membership_id': membership_id
        })

        if kwargs['ip_address']:
            user['ip_info'] = kwargs.get('ip_info')

        custom = convert_custom_header_json(request.headers)
        await asyncio.gather(
            reset_user_password(app.db, user, password),
            app.persist_event.on_event(Event(**{
                'document': user,
                'user': user,
                'type': 'PasswordResetEvent',
                'username': user['username'].lower(),
                'membership_id': user['membership_id'],
                'custom': custom,
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            }))
        )

        await revoke_and_delete_old_active_tokens(user, app.db)

        return json({}, 204)

    # endregion

    # region Change Password
    @app.route('/api/v1/change-password', methods=['POST'])
    @authorized(app, settings, methods=['POST'])
    @validated(CHANGE_PASSWORD_SCHEMA)
    @resolve_ip()
    async def change_password(request, **kwargs):
        user = kwargs.get('user')
        body = request.json

        user_id = body.get('user_id')
        password = body.get('password')
        password_confirm = body.get('password_confirm')

        if user_id != str(user['_id']):
            raise BlupointError(
                err_msg="User cannot change other users password",
                err_code="errors.userCannotChangeOthersPassword",
                status_code=403
            )

        if password != password_confirm:
            raise BlupointError(
                err_code="errors.passwordAndPasswordConfirmDoesNotMatch",
                err_msg="Password and password confirm does not match",
                status_code=400
            )

        if kwargs['ip_address']:
            user['ip_info'] = kwargs.get('ip_info')

        custom = convert_custom_header_json(request.headers)
        hashed_password = hash_user_password(password)
        await asyncio.gather(
            update_user_with_body(
                app.db, user_id, user['membership_id'],
                {'password': hashed_password, 'ip_info': user.get('ip_info', {})}
            ),
            app.persist_event.on_event(Event(**{
                'document': user,
                'user': user,
                'type': 'PasswordChangedEvent',
                'username': user['username'].lower(),
                'membership_id': user['membership_id'],
                'custom': custom,
                'sys': {
                    'created_at': datetime.datetime.utcnow()
                }
            }))
        )

        return json({}, 200)

    # endregion
