import json
from sanic import response
from src.plugins.authorization import authorized, TokenTypes, UtilizerTypes
from src.utils.errors import ErtisError
from src.utils.json_helpers import bson_to_json


def init_me_api(app, settings):
    # region ME Api
    @app.route('/api/v1/me', methods=['GET'])
    @authorized(app, settings, methods=['GET'])
    async def me_api(request, **kwargs):
        if request.ctx.utilizer_type == UtilizerTypes.USER:
            utilizer = await app.bearer_token_service.me(request.ctx.utilizer)
        elif request.ctx.utilizer_type == UtilizerTypes.APPLICATION:
            utilizer = await app.basic_token_service.me(request.ctx.utilizer)
        else:
            raise ErtisError(
                err_code="errors.authorizationError",
                err_msg="Unsupported authorization header",
                status_code=401
            )

        return response.json(json.loads(json.dumps(utilizer, default=bson_to_json)))
    # endregion
