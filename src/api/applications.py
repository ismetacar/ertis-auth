import json

from sanic import response
from sanic_openapi import doc

from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.request_models.applications import Application
from src.request_models.query_model import Query
from src.resources.applications.applications import APPLICATION_CREATE_SCHEMA
from src.resources.generic import QUERY_BODY_SCHEMA, ensure_membership_is_exists
from src.utils import query_helpers
from src.utils.json_helpers import bson_to_json


def init_applications_api(app, settings):
    # region Create Application
    @app.route('/api/v1/memberships/<membership_id>/applications', methods=['POST'])
    @doc.tag("Applications")
    @doc.operation("Create Application")
    @doc.consumes(Application, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='applications.create')
    @validated(APPLICATION_CREATE_SCHEMA)
    async def create_application(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)

        body = request.json
        resource = await app.application_service.create_application(body, request.ctx.utilizer, app.persist_event)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 201)

    # endregion

    # region Get Application
    @app.route('/api/v1/memberships/<membership_id>/applications/<application_id>', methods=['GET'])
    @doc.tag("Applications")
    @doc.operation("Get Application")
    @authorized(app, settings, methods=['GET'], required_permission='applications.read')
    async def get_application(request, membership_id, application_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        resource = await app.application_service.get_application(application_id, request.ctx.utilizer)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)))

    # endregion

    # region Update Application
    @app.route('/api/v1/memberships/<membership_id>/applications/<application_id>', methods=['PUT'])
    @doc.tag("Applications")
    @doc.operation("Update Application")
    @doc.consumes(Application, location="body", content_type="application/json")
    @authorized(app, settings, methods=['PUT'], required_permission='applications.update')
    async def update_application(request, membership_id, application_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        resource = await app.application_service.update_application(application_id, body, request.ctx.utilizer, app.persist_event)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Delete Application
    @app.route('/api/v1/memberships/<membership_id>/applications/<application_id>', methods=['DELETE'])
    @doc.tag("Applications")
    @doc.operation("Delete Application")
    @authorized(app, settings, methods=['DELETE'], required_permission='applications.delete')
    async def delete_application(request, membership_id, application_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        await app.application_service.delete_application(application_id, request.ctx.utilizer, app.persist_event)

        return response.json({}, 204)

    # endregion

    # region Query Applications
    # noinspection DuplicatedCode
    @app.route('/api/v1/memberships/<membership_id>/applications/_query', methods=['POST'])
    @doc.tag("Applications")
    @doc.operation("Query Applications")
    @doc.consumes(Query, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='applications.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_applications(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        where, select, limit, skip, sort = query_helpers.parse(request)
        applications, count = await app.application_service.query_applications(
            membership_id,
            where,
            select,
            limit,
            skip,
            sort
        )
        response_json = json.loads(json.dumps({
            'data': {
                'items': applications,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json, 200)

    # endregion
