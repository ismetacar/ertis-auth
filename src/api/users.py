import json

from sanic import response
from sanic_openapi import doc

from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.request_models.query_model import Query
from src.request_models.users import User
from src.resources.generic import QUERY_BODY_SCHEMA, ensure_membership_is_exists
from src.utils import query_helpers
from src.utils.errors import ErtisError
from src.utils.json_helpers import bson_to_json


def init_users_api(app, settings):
    # region Create User
    @app.route('/api/v1/memberships/<membership_id>/users', methods=['POST'])
    @doc.tag("Users")
    @doc.operation("Create User")
    @doc.consumes(User, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='users.create')
    async def create_user(request, membership_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        resource = await app.user_service.create_user(body, membership_id, request.ctx.utilizer, app.user_type_service,
                                                      app.persist_event)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 201)

    # endregion

    # region Get User
    @app.route('/api/v1/memberships/<membership_id>/users/<user_id>', methods=['GET'])
    @doc.tag("Users")
    @doc.operation("Get User")
    @authorized(app, settings, methods=['GET'], required_permission='users.read')
    async def get_user(request, membership_id, user_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)

        resource = await app.user_service.get_user(user_id, request.ctx.utilizer)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Update User
    @app.route('/api/v1/memberships/<membership_id>/users/<user_id>', methods=['PUT'])
    @doc.tag("Users")
    @doc.operation("Update User")
    @doc.consumes(User, location="body", content_type="application/json")
    @authorized(app, settings, methods=['PUT'], required_permission='users.update')
    async def update_user(request, membership_id, user_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        if body.get("password"):
            raise ErtisError(
                err_msg="User password can not updatable with UpdateUser endpoint.",
                err_code="errors.passwordCanNotUpdated",
                status_code=301,
                context={
                    "from": f"/api/v1/memberships/{membership_id}/users/{user_id}",
                    "to": "/api/v1/change-password"
                }
            )

        resource = await app.user_service.update_user(user_id, body, request.ctx.utilizer, app.user_type_service,
                                                      app.persist_event)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Delete User
    @app.route('/api/v1/memberships/<membership_id>/users/<user_id>', methods=['DELETE'])
    @doc.tag("Users")
    @doc.operation("Delete User")
    @authorized(app, settings, methods=['DELETE'], required_permission='users.delete')
    async def delete_user(request, membership_id, user_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)

        await app.user_service.delete_user(user_id, request.ctx.utilizer, app.persist_event)
        return response.json({}, 204)

    # endregion

    # region Query Users
    @app.route('/api/v1/memberships/<membership_id>/users/_query', methods=['POST'])
    @doc.tag("Users")
    @doc.operation("Query Users")
    @doc.consumes(Query, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='users.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_users(request, membership_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        where, select, limit, skip, sort = query_helpers.parse(request)
        users, count = await app.user_service.query_users(membership_id, where, select, limit, skip, sort)

        response_json = json.loads(json.dumps({
            'data': {
                'items': users,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json)
    # endregion
