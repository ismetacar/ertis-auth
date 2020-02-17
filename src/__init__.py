import logging

from sanic import Sanic


def create_sanic_app(settings):
    app = Sanic(load_env='AUTH_')
    app.logger = logging.getLogger('create_app')

    for key in settings.keys():
        settings[key] = getattr(app.config, key.upper(), settings[key])

    from src.plugins import init_plugins
    init_plugins(app, settings)

    from src.api.healthcheck import init_healthcheck_api
    init_healthcheck_api(app, settings)

    from src.api.ip_resolver import init_ip_resolver_api
    init_ip_resolver_api(app, settings)

    from src.api.tokens import init_token_api
    init_token_api(app, settings)

    from src.api.me import init_me_api
    init_me_api(app, settings)

    from src.api.users import init_users_api
    init_users_api(app, settings)

    from src.api.applications import init_applications_api
    init_applications_api(app, settings)

    from src.api.roles import init_roles_api
    init_roles_api(app, settings)

    from src.api.routes import init_routes_api
    init_routes_api(app, settings)

    return app
