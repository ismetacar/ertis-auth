import json

from sanic import response
from sanic_openapi import doc

from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.request_models.providers import Provider
from src.request_models.query_model import Query
from src.resources.generic import ensure_membership_is_exists, QUERY_BODY_SCHEMA
from src.resources.providers.resource import CREATE_PROVIDER_SCHEMA
from src.utils import query_helpers
from src.utils.json_helpers import bson_to_json


def init_providers_api(app, settings):
    # region Create Provider
    @app.route('/api/v1/memberships/<membership_id>/providers', methods=['POST'])
    @doc.tag("Providers")
    @doc.operation("Create Provider")
    @doc.consumes(Provider, location="body", content_type="application/json")
    @validated(CREATE_PROVIDER_SCHEMA)
    @authorized(app, settings, methods=['POST'], required_permission='providers.create')
    async def create_provider(request, membership_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)

        body = request.json
        resource = await app.provider_service.create_provider(body, request.ctx.utilizer)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 201)

    # endregion

    # region Get Provider
    @app.route('/api/v1/memberships/<membership_id>/providers/<provider_id>', methods=['GET'])
    @doc.tag("Providers")
    @doc.operation("Get Provider")
    @authorized(app, settings, methods=['GET'], required_permission='providers.read')
    async def get_provider(request, membership_id, provider_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        resource = await app.provider_service.get_provider(provider_id, request.ctx.utilizer)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)))

    # endregion

    # region Update Provider
    @app.route('/api/v1/memberships/<membership_id>/providers/<provider_id>', methods=['PUT'])
    @doc.tag("Providers")
    @doc.operation("Update Provider")
    @doc.consumes(Provider, location="body", content_type="application/json")
    @authorized(app, settings, methods=['PUT'], required_permission='providers.update')
    async def update_provider(request, membership_id, provider_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        body = request.json
        resource = await app.provider_service.update_provider(provider_id, body, request.ctx.utilizer,
                                                              app.persist_event)

        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Delete Provider
    @app.route('/api/v1/memberships/<membership_id>/providers/<provider_id>', methods=['DELETE'])
    @doc.tag("Providers")
    @doc.operation("Delete Provider")
    @authorized(app, settings, methods=['DELETE'], required_permission='providers.delete')
    async def delete_provider(request, membership_id, provider_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        await app.provider_service.delete_provider(provider_id, request.ctx.utilizer, app.persist_event)

        return response.json({}, 204)

    # endregion

    # region Query Applications
    # noinspection DuplicatedCode
    @app.route('/api/v1/memberships/<membership_id>/providers/_query', methods=['POST'])
    @doc.tag("Providers")
    @doc.operation("Query Providers")
    @doc.consumes(Query, location="body", content_type="application/json")
    @authorized(app, settings, methods=['POST'], required_permission='providers.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_providers(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        where, select, limit, skip, sort = query_helpers.parse(request)
        providers, count = await app.provider_service.query_providers(
            membership_id,
            where,
            select,
            limit,
            skip,
            sort
        )
        response_json = json.loads(json.dumps({
            'data': {
                'items': providers,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json, 200)

    # endregion
