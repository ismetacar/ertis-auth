import json
from sanic import response
from sanic_openapi import doc

from src.request_models.query_model import Query
from src.request_models.roles import Role
from src.utils import query_helpers
from src.plugins.validator import validated
from src.utils.json_helpers import bson_to_json
from src.plugins.authorization import authorized
from src.resources.generic import QUERY_BODY_SCHEMA, ensure_membership_is_exists
from src.resources.roles.roles import ROLE_CRETE_SCHEMA


def init_roles_api(app, settings):
    # region Create Role
    @app.route('/api/v1/memberships/<membership_id>/roles', methods=['POST'])
    @doc.tag("Roles")
    @doc.operation("Create Role")
    @doc.consumes(Role, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='roles.create')
    @validated(ROLE_CRETE_SCHEMA)
    async def create_role(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)

        body = request.json
        resource = await app.role_service.create_role(body, request.ctx.utilizer, app.persist_event)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 201)

    # endregion

    # region Get Role
    @app.route('/api/v1/memberships/<membership_id>/roles/<role_id>', methods=['GET'])
    @doc.tag("Roles")
    @doc.operation("Get Role")
    @authorized(app, settings, methods=['GET'], required_permission='roles.read')
    async def get_role(request, membership_id, role_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        resource = await app.role_service.get_role(role_id, membership_id)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Update Role
    @app.route('/api/v1/memberships/<membership_id>/roles/<role_id>', methods=['PUT'])
    @doc.tag("Roles")
    @doc.operation("Update Role")
    @doc.consumes(Role, location="body", content_type="application/json")
    @authorized(app, settings, methods=['PUT'], required_permission='roles.update')
    async def update_role(request, membership_id, role_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        resource = await app.role_service.update_role(role_id, body, request.ctx.utilizer, app.persist_event)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)))

    # endregion

    # region Delete Role
    @app.route('/api/v1/memberships/<membership_id>/roles/<role_id>', methods=['DELETE'])
    @doc.tag("Roles")
    @doc.operation("Delete Role")
    @authorized(app, settings, methods=['DELETE'], required_permission='roles.delete')
    async def delete_role(request, membership_id, role_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        await app.role_service.delete_role(role_id, request.ctx.utilizer, app.persist_event)
        return response.json({}, 204)

    # endregion

    # region Query Roles
    @app.route('/api/v1/memberships/<membership_id>/roles/_query', methods=['POST'])
    @doc.tag("Roles")
    @doc.operation("Query Roles")
    @doc.consumes(Query, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='roles.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_roles(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)

        where, select, limit, skip, sort = query_helpers.parse(request)
        roles, count = await app.role_service.query_roles(membership_id, where, select, limit, skip, sort)
        response_json = json.loads(json.dumps({
            'data': {
                'items': roles,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json)
    # endregion
