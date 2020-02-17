import json

from sanic import response

from src.plugins.authorization import authorized
from src.utils.json_helpers import bson_to_json


def init_me_api(app, settings):
    # region ME Api
    @app.route('/api/v1/me', methods=['GET'])
    @authorized(app, settings, methods=['GET'])
    async def me_api(request, **kwargs):
        user = kwargs.get('user')

        user_role = await app.db.roles.find_one({
            'slug': user['role'],
            'membership_id': user['membership_id']
        })

        user_permissions = user_role.get('permissions', []) if user_role else []
        user['role_permissions'] = user_permissions

        user.pop('password', None)
        user.pop('decoded_token', None)
        user = json.loads(json.dumps(user, default=bson_to_json))
        return response.json(user)
    # endregion
