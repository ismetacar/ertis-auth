import copy
import datetime
import json

from sanic import response

from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.resources.applications import (
    ensure_name_is_unique_in_membership,
    generate_app_secrets,
    find_application,
    pop_non_updatable_fields,
    update_application_with_body,
    remove_application,
    APPLICATION_CREATE_SCHEMA
)
from src.resources.generic import query, QUERY_BODY_SCHEMA, ensure_membership_is_exists
from src.utils import query_helpers
from src.utils.errors import BlupointError
from src.utils.json_helpers import bson_to_json


def init_applications_api(app, settings):
    # region Create Application
    @app.route('/api/v1/memberships/<membership_id>/applications', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='applications.create')
    @validated(APPLICATION_CREATE_SCHEMA)
    async def create_application(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        application = request.json
        application['membership_id'] = membership_id
        application['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': kwargs.get('user')['username']
        }

        await ensure_name_is_unique_in_membership(app.db, application)
        application = generate_app_secrets(application)
        app_id = await app.db.applications.insert_one(application)
        application['_id'] = str(app_id.inserted_id)

        application = json.loads(json.dumps(application, default=bson_to_json))
        return response.json(application, 201)

    # endregion

    # region Get Application
    @app.route('/api/v1/memberships/<membership_id>/applications/<application_id>', methods=['GET'])
    @authorized(app, settings, methods=['GET'], required_permission='applications.read')
    async def get_application(request, membership_id, application_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        application = await find_application(app.db, membership_id, application_id)
        application = json.loads(json.dumps(application, default=bson_to_json))

        return response.json(application)

    # endregion

    # region Update Application
    @app.route('/api/v1/memberships/<membership_id>/applications/<application_id>', methods=['PUT'])
    @authorized(app, settings, methods=['PUT'], required_permission='applications.update')
    async def update_application(request, membership_id, application_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))
        application = await find_application(app.db, membership_id, application_id)

        _application = copy.deepcopy(application)

        body = request.json
        provided_body = pop_non_updatable_fields(body)

        application.update(provided_body)
        if application == _application:
            raise BlupointError(
                err_msg="Identical document error",
                err_code="errors.identicalDocument",
                status_code=409
            )

        application['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': kwargs.get('user')['username']
        })

        provided_body['sys'] = application['sys']
        application = await update_application_with_body(app.db, application_id, membership_id, provided_body)
        application = json.loads(json.dumps(application, default=bson_to_json))

        return response.json(application)

    # endregion

    # region Delete Application
    @app.route('/api/v1/memberships/<membership_id>/applications/<application_id>', methods=['DELETE'])
    @authorized(app, settings, methods=['DELETE'], required_permission='applications.delete')
    async def delete_application(request, membership_id, application_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))
        await remove_application(app.db, membership_id, application_id)

        return response.json({}, 204)

    # endregion

    # region Query Applications
    @app.route('/api/v1/memberships/<membership_id>/applications/_query', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='applications.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_applications(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))
        where, select, limit, sort, skip = query_helpers.parse(request)
        applications, count = await query(app.db, where, select, limit, skip, sort, 'applications')
        response_json = json.loads(json.dumps({
            'data': {
                'items': applications,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json)

    # endregion
