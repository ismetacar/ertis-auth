import json
from sanic import response
from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.resources.generic import ensure_membership_is_exists
from src.resources.user_types.validation import CREATE_SCHEMA
from src.utils.json_helpers import bson_to_json


def init_user_types_api(app, settings):
    # region Create User Type
    @app.route('/api/v1/memberships/<membership_id>/user-types', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='user_types.create')
    @validated(CREATE_SCHEMA)
    async def create_user_type(request, membership_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        resource = await app.user_type_service.create_user_type(body, request.ctx.utilizer, app.persist_event)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 201)

    # endregion

    # region Get User Type of Membership
    @app.route('/api/v1/memberships/<membership_id>/get-user-type', methods=['GET'])
    @authorized(app, settings, methods=['GET'])
    async def get_user_type_of_membership(request, membership_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        resource = await app.user_type_service.get_user_type(membership_id, user_type_id=None)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)
    # endregion

    # region Get User Type By Id
    @app.route('/api/v1/memberships/<membership_id>/user-types/<user_type_id>', methods=['GET'])
    @authorized(app, settings, methods=['GET'])
    async def get_user_type(request, membership_id, user_type_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        resource = await app.user_type_service.get_user_type(membership_id, user_type_id=user_type_id)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Update User Type
    @app.route('/api/v1/memberships/<membership_id>/user-types/<user_type_id>', methods=['PUT'])
    @authorized(app, settings, methods=['PUT'])
    async def update_user_type(request, membership_id, user_type_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        resource = await app.user_type_service.update_user_type(user_type_id, body, request.ctx.utilizer, app.persist_event)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion
