import json
from sanic import response
from src.plugins.authorization import authorized
from src.utils.json_helpers import bson_to_json


def init_me_api(app, settings):
    # region ME Api
    @app.route('/api/v1/me', methods=['GET'])
    @authorized(app, settings, methods=['GET'])
    async def me_api(request, **kwargs):
        user = await app.bearer_token_service.me(request.ctx.user)
        user = json.loads(json.dumps(user, default=bson_to_json))
        return response.json(user)
    # endregion
