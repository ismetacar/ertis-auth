from sanic.response import json
from sanic_openapi import doc


def init_healthcheck_api(app, settings):
    @app.route('/api/v1/healthcheck', methods=['GET'])
    @doc.tag("Healthcheck")
    @doc.operation("Get Healthy Status")
    async def healthcheck(request):
        return json({
            'healthcheck': True
        }, 200)
