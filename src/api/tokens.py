import json
from sanic import response
from src.plugins.validator import validated
from src.plugins.authorization import authorized
from src.resources.generic import ensure_membership_is_exists
from src.resources.tokens.tokens import (
    SET_PASSWORD_SCHEMA,
    CREATE_TOKEN_SCHEMA,
    REFRESH_TOKEN_SCHEMA,
    RESET_PASSWORD_SCHEMA
)
from src.resources.users.users import CHANGE_PASSWORD_SCHEMA
from src.utils.json_helpers import bson_to_json


def init_token_api(app, settings):
    # region Generate Token
    @app.route('/api/v1/generate-token', methods=['POST'])
    @validated(CREATE_TOKEN_SCHEMA)
    async def create_token(request, **kwargs):
        body = request.json
        auth_header = request.headers.get('authorization', None)
        membership_id = request.headers.get('x-ertis-alias', None)

        await ensure_membership_is_exists(app.db, membership_id, user=None)

        result = await app.bearer_token_service.generate_token(
            auth_header,
            settings,
            membership_id,
            body,
            app.persist_event
        )

        return response.json(json.loads(json.dumps(result[0], default=bson_to_json)), 201)

    # endregion

    # region Refresh Token
    @app.route('/api/v1/refresh-token', methods=['POST'])
    @validated(REFRESH_TOKEN_SCHEMA)
    async def refresh_token(request, **kwargs):
        body = request.json
        refreshable_token = body['token']
        do_revoke = request.args.get('revoke', 'true').lower()

        refreshed_token = await app.bearer_token_service.refresh_token(
            do_revoke,
            refreshable_token,
            settings,
            app.persist_event
        )

        return response.json(json.loads(json.dumps(refreshed_token, default=bson_to_json)), 200)

    # endregion

    # region Verify Token
    @app.route('/api/v1/verify-token', methods=['POST'])
    @validated(REFRESH_TOKEN_SCHEMA)
    async def verify_token(request, **kwargs):
        body = request.json
        token = body['token']

        token_response = await app.bearer_token_service.verify_token(token, settings, app.persist_event)

        return response.json(json.loads(json.dumps(token_response, default=bson_to_json)), 200)

    # endregion

    # region Revoke Token
    @app.route('/api/v1/revoke-token', methods=['POST'])
    @validated(REFRESH_TOKEN_SCHEMA)
    async def revoke_token(request, **kwargs):
        body = request.json
        token = body['token']
        await app.bearer_token_service.revoke_token(token, settings, app.persist_event)

        return response.json({}, 204)

    # endregion

    # region Reset Password
    @app.route('/api/v1/reset-password', methods=['POST'])
    @validated(RESET_PASSWORD_SCHEMA)
    async def reset_password(request, **kwargs):
        membership_id = request.headers.get('x-ertis-alias', None)
        body = request.json
        await ensure_membership_is_exists(app.db, membership_id, user=None)

        user = await app.password_service.reset_password(body, membership_id, app.persist_event)
        return response.json(user['reset_password'], 200)

    # endregion

    # region Set New Password
    @app.route('/api/v1/set-password', methods=['POST'])
    @validated(SET_PASSWORD_SCHEMA)
    async def set_password(request, **kwargs):
        membership_id = request.headers.get('x-ertis-alias', None)
        body = request.json
        await ensure_membership_is_exists(app.db, membership_id, user=None)

        await app.password_service.set_password(body, membership_id, app.persist_event)
        return response.json({}, 204)

    # endregion

    # region Change Password
    @app.route('/api/v1/change-password', methods=['POST'])
    @authorized(app, settings, methods=['POST'])
    @validated(CHANGE_PASSWORD_SCHEMA)
    async def change_password(request, **kwargs):
        user = request.ctx.user
        body = request.json
        await app.password_service.change_password(body, user, app.persist_event)

        return response.json({}, 200)

    # endregion
