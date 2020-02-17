import copy
import datetime
import json

from sanic import response

from src.plugins.authorization import authorized
from src.plugins.validator import validated
from src.resources.generic import query, QUERY_BODY_SCHEMA, ensure_membership_is_exists
from src.resources.users import (
    hash_user_password,
    ensure_email_and_username_available,
    set_nullable_fields,
    find_user,
    pop_non_updatable_fields,
    update_user_with_body,
    remove_user,
    ensure_provided_role_is_exists, pop_critical_user_fields,
    USER_CREATE_SCHEMA,
    prepare_user_fields, revoke_and_delete_old_active_tokens)
from src.utils import query_helpers
from src.utils.errors import BlupointError
from src.utils.json_helpers import bson_to_json


def init_users_api(app, settings):
    # region Create User
    @app.route('/api/v1/memberships/<membership_id>/users', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='users.create')
    @validated(USER_CREATE_SCHEMA)
    async def create_user(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        user = request.json
        user = prepare_user_fields(user, membership_id, request.json['password'])
        await ensure_email_and_username_available(app.db, user)
        await ensure_provided_role_is_exists(app.db, user, membership_id)

        user['sys'] = {
            'created_at': datetime.datetime.utcnow(),
            'created_by': kwargs.get('user')['username']
        }

        user = set_nullable_fields(user)
        await app.db.users.insert_one(user)
        user.pop('password', None)

        user = json.loads(json.dumps(user, default=bson_to_json))
        return response.json(user, 201)

    # endregion

    # region Get User
    @app.route('/api/v1/memberships/<membership_id>/users/<user_id>', methods=['GET'])
    @authorized(app, settings, methods=['GET'], required_permission='users.read')
    async def get_user(request, membership_id, user_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        user = await find_user(app.db, user_id, membership_id)
        user = json.loads(json.dumps(user, default=bson_to_json))
        user.pop('password', None)
        user.pop('token', None)

        return response.json(user)

    # endregion

    # region Update User
    @app.route('/api/v1/memberships/<membership_id>/users/<user_id>', methods=['PUT'])
    @authorized(app, settings, methods=['PUT'], required_permission='users.update')
    async def update_user(request, membership_id, user_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        user = await find_user(app.db, user_id, membership_id)

        body = request.json
        provided_body = pop_non_updatable_fields(body)
        if body.get('password'):
            if body['password'] != user['password']:
                body['password'] = hash_user_password(body['password'])
                await revoke_and_delete_old_active_tokens(user, app.db)
            else:
                body.pop('password', None)

        user = prepare_user_fields(user, membership_id, request.json.get('password'), opt='update')

        _user = copy.deepcopy(user)
        _user.update(provided_body)
        if _user == user:
            raise BlupointError(
                err_code="errors.identicalDocument",
                err_msg="Identical document error",
                status_code=409
            )

        if _user['username'] != user['username']:
            await revoke_and_delete_old_active_tokens(_user, app.db)

        user['sys'].update({
            'modified_at': datetime.datetime.utcnow(),
            'modified_by': kwargs.get('user')['username']
        })

        provided_body['sys'] = user['sys']

        user = await update_user_with_body(app.db, user_id, membership_id, provided_body)
        user = json.loads(json.dumps(user, default=bson_to_json))
        user.pop('password')

        return response.json(user)

    # endregion

    # region Delete User
    @app.route('/api/v1/memberships/<membership_id>/users/<user_id>', methods=['DELETE'])
    @authorized(app, settings, methods=['DELETE'], required_permission='users.delete')
    async def delete_user(request, membership_id, user_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))

        if str(kwargs.get('user')['_id']) == user_id:
            raise BlupointError(
                err_code="errors.userCannotDeleteHerself",
                err_msg="User can not delete herself",
                status_code=400
            )
        await remove_user(app.db, user_id, membership_id)
        return response.json({}, 204)

    # endregion

    # region Query Users
    @app.route('/api/v1/memberships/<membership_id>/users/_query', methods=['POST'])
    @authorized(app, settings, methods=['POST'], required_permission='users.read')
    @validated(QUERY_BODY_SCHEMA)
    async def query_users(request, membership_id, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, kwargs.get('user'))
        where, select, limit, sort, skip = query_helpers.parse(request)
        users, count = await query(app.db, where, select, limit, skip, sort, 'users')

        users = pop_critical_user_fields(users)
        response_json = json.loads(json.dumps({
            'data': {
                'items': users,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json)
    # endregion
