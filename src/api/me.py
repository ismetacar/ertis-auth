import json
from sanic import response
from src.plugins.authorization import authorized, TokenTypes
from src.utils.json_helpers import bson_to_json


def init_me_api(app, settings):
    # region ME Api
    @app.route('/api/v1/me', methods=['GET'])
    @authorized(app, settings, methods=['GET'], allowed_token_types=[TokenTypes.BEARER])
    async def me_api(request, **kwargs):
        user = await app.bearer_token_service.me(request.ctx.utilizer)
        user = json.loads(json.dumps(user, default=bson_to_json))
        return response.json(user)
    # endregion
