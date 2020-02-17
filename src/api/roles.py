import copy
import datetime
import json
from sanic import response
from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.resources.generic import query, QUERY_BODY_SCHEMA, ensure_membership_is_exists
from src.resources.roles import (
    generate_slug,
    check_slug_conflict,
    find_role,
    update_role_with_body,
    pop_non_updatable_fields,
    remove_role,
    ROLE_CRETE_SCHEMA
)
from src.utils import query_helpers
from src.utils.errors import BlupointError
from src.utils.json_helpers import bson_to_json


def init_roles_api(app, settings):
    # region Create Role
    @app.route('/api/v1/memberships/<membership_id>/roles', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='roles.create')
    @validated(ROLE_CRETE_SCHEMA)
    async def create_role(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        body = request.json
        role = generate_slug(body)
        role['membership_id'] = membership_id

        role = await check_slug_conflict(app.db, role)
        role['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': kwargs.get('user')['username']
        }
        saved_role = await app.db.roles.insert_one(role)

        role['_id'] = str(saved_role.inserted_id)
        role = json.loads(json.dumps(role, default=bson_to_json))

        return response.json(role, 201)
    # endregion

    # region Get Role
    @app.route('/api/v1/memberships/<membership_id>/roles/<role_id>', methods=['GET'])
    @authorized(app, settings, methods=['GET'], required_permission='roles.read')
    async def get_role(request, membership_id, role_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        role = await find_role(app.db, role_id, membership_id)
        role = json.loads(json.dumps(role, default=bson_to_json))

        return response.json(role)
    # endregion

    # region Update Role
    @app.route('/api/v1/memberships/<membership_id>/roles/<role_id>', methods=['PUT'])
    @authorized(app, settings, methods=['PUT'], required_permission='roles.update')
    async def update_role(request, membership_id, role_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))
        body = request.json
        provided_body = pop_non_updatable_fields(body)

        role = await find_role(app.db, role_id, membership_id)
        _role = copy.deepcopy(role)
        _role.update(provided_body)
        if _role == role:
            raise BlupointError(
                err_code="errors.identicalDocument",
                err_msg="Identical document error",
                status_code=409
            )

        role['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': kwargs.get('user')['username']
        })

        provided_body['sys'] = role['sys']

        role = await update_role_with_body(app.db, role_id, membership_id, provided_body)
        role = json.loads(json.dumps(role, default=bson_to_json))

        return response.json(role)
    # endregion

    # region Delete Role
    @app.route('/api/v1/memberships/<membership_id>/roles/<role_id>', methods=['DELETE'])
    @authorized(app, settings, methods=['DELETE'], required_permission='roles.delete')
    async def delete_role(request, membership_id, role_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))
        await remove_role(app.db, role_id, membership_id)

        return response.json({}, 204)

    # endregion

    # region Query Roles
    @app.route('/api/v1/memberships/<membership_id>/roles/_query', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='roles.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_roles(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        where, select, limit, sort, skip = query_helpers.parse(request)
        users, count = await query(app.db, where, select, limit, skip, sort, 'roles')
        response_json = json.loads(json.dumps({
            'data': {
                'items': users,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json)
    # endregion
