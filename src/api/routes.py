from sanic.response import json


def init_routes_api(app, settings):
    @app.route('/api/v1/api-map')
    async def all_routes(request):
        links = []
        for handler, (rule, router) in app.router.routes_names.items():
            options = {}
            for arg in router.parameters:
                options[arg] = "[{0}]".format(arg)

            methods = ','.join(router.methods)

            line = "{:80s} {}".format(rule, methods)
            links.append(line)

        return json(links)
