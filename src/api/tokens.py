import json
from sanic import response
from sanic_openapi import doc

from src.plugins.validator import validated
from src.plugins.authorization import authorized, TokenTypes
from src.request_models.tokens import GenerateToken, RefreshToken, VerifyToken, RevokeToken, ResetPassword, SetPassword, \
    ChangePassword
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
    @doc.tag("Tokens")
    @doc.operation("Create Token")
    @doc.consumes(GenerateToken, location="body", content_type="application/json")
    @doc.consumes(doc.String(name="X-Ertis-Alias"), location="header", required=True)
    @validated(CREATE_TOKEN_SCHEMA)
    async def create_token(request, **kwargs):
        body = request.json
        membership_id = request.headers.get('x-ertis-alias', None)

        membership = await ensure_membership_is_exists(app.db, membership_id, user=None)

        token = await app.bearer_token_service.generate_token(
            settings,
            membership,
            body,
            app.persist_event
        )

        return response.json(json.loads(json.dumps(token, default=bson_to_json)), 201)

    # endregion

    # region Refresh Token
    @app.route('/api/v1/refresh-token', methods=['POST'])
    @doc.tag("Tokens")
    @doc.operation("Refresh Token")
    @doc.consumes(RefreshToken, location="body", content_type="application/json")
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
    @doc.tag("Tokens")
    @doc.operation("Verify Token")
    @doc.consumes(VerifyToken, location="body", content_type="application/json")
    @validated(REFRESH_TOKEN_SCHEMA)
    async def verify_token(request, **kwargs):
        body = request.json
        token = body['token']

        token_response = await app.bearer_token_service.verify_token(token, settings, app.persist_event)

        return response.json(json.loads(json.dumps(token_response, default=bson_to_json)), 200)

    # endregion

    # region Revoke Token
    @app.route('/api/v1/revoke-token', methods=['POST'])
    @doc.tag("Tokens")
    @doc.operation("Revoke Token")
    @doc.consumes(RevokeToken, location="body", content_type="application/json")
    @validated(REFRESH_TOKEN_SCHEMA)
    async def revoke_token(request, **kwargs):
        body = request.json
        token = body['token']
        await app.bearer_token_service.revoke_token(token, settings, app.persist_event)

        return response.json({}, 204)

    # endregion

    # region Reset Password
    @app.route('/api/v1/reset-password', methods=['POST'])
    @doc.tag("Password")
    @doc.operation("Reset Password")
    @doc.consumes(ResetPassword, location="body", content_type="application/json")
    @doc.consumes(doc.String(name="X-Ertis-Alias"), location="header", required=True)
    @validated(RESET_PASSWORD_SCHEMA)
    async def reset_password(request, **kwargs):
        membership_id = request.headers.get('x-ertis-alias', None)
        body = request.json
        await ensure_membership_is_exists(app.db, membership_id, user=None)

        user = await app.password_service.reset_password(body, membership_id, app.persist_event)
        return response.json(json.loads(json.dumps(user['reset_password'], default=bson_to_json)), 200)

    # endregion

    # region Set New Password
    @app.route('/api/v1/set-password', methods=['POST'])
    @doc.tag("Password")
    @doc.operation("Set New Password")
    @doc.consumes(SetPassword, location="body", content_type="application/json")
    @doc.consumes(doc.String(name="X-Ertis-Alias"), location="header", required=True)
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
    @doc.tag("Password")
    @doc.operation("Change Password")
    @doc.consumes(ChangePassword, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], allowed_token_types=[TokenTypes.BEARER])
    @validated(CHANGE_PASSWORD_SCHEMA)
    async def change_password(request, **kwargs):
        user = request.ctx.utilizer
        body = request.json
        await app.password_service.change_password(body, user, app.persist_event)

        return response.json({}, 200)

    # endregion
