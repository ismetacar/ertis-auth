from sanic.response import json


def init_healthcheck_api(app, settings):
    @app.route('/api/v1/healthcheck', methods=['GET'])
    async def healthcheck(request):
        return json({
            'healthcheck': True
        }, 200)
