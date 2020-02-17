import logging
import raven
from raven_aiohttp import AioHttpTransport

logging.basicConfig(level=logging.INFO)
plugins_logger = logging.getLogger('plugins')


def init_plugins(app, settings):
    from src.plugins.startup import init_startup_methods
    init_startup_methods(app, settings)

    from .error_handler import init_error_handler
    sentry_client = raven.Client(settings['sentry_connection_string'], transport=AioHttpTransport)
    init_error_handler(app, settings, sentry_client=sentry_client)
