from sanic import response
from sanic.exceptions import MethodNotSupported, NotFound, InvalidUsage
from sanic.handlers import ErrorHandler
from sanic_sentry import safe_getattr

from src.utils.errors import ErtisError


def _request_debug_info(request):
    return dict(
        url=safe_getattr(request, "url"),
        method=safe_getattr(request, "method"),
        headers=safe_getattr(request, "headers"),
        body=safe_getattr(request, "body"),
        query_string=safe_getattr(request, "query_string"),
    )


class CustomErrorHandler(ErrorHandler):
    def __init__(self, settings, sentry_client):
        super().__init__()
        self.settings = settings
        self.sentry_client = sentry_client

    def default(self, request, exception):
        if isinstance(exception, ErtisError):
            return response.json(
                body={
                    'err_msg': exception.err_msg,
                    'err_code': exception.err_code,
                    'context': exception.context,
                    'reason': exception.reason
                },
                status=exception.status_code
            )

        elif isinstance(exception, MethodNotSupported):
            return response.json(
                body={
                    'err_msg': 'Method not allowed: <{}>'.format(request.method),
                    'err_code': 'errors.methodNotAllowed'
                },
                status=405
            )

        elif isinstance(exception, InvalidUsage):
            return response.json(
                body={
                    'err_msg': 'Invalid usage detected. <{}>'.format(str(exception)),
                    'err_code': 'errors.invalidUsage'
                },
                status=400
            )

        elif isinstance(exception, NotFound):
            return response.json(
                body={
                    'err_msg': 'Api endpoint is not found',
                    'err_code': 'errors.apiEndpointNotFound'
                },
                status=404
            )

        else:
            exc_info = (type(exception), exception, exception.__traceback__)
            extra = _request_debug_info(request) if request else dict()
            self.sentry_client.captureException(exc_info, extra=extra)
            return response.json(
                body={
                    'err_msg': "{} - {}".format(type(exception).__name__, str(exception)),
                    'err_code': "errors.internalServerError",
                },
                status=500
            )


def init_error_handler(app, settings, sentry_client):
    app.logger.info('Error handler initialized.')

    if settings['error_handler']:
        app.error_handler = CustomErrorHandler(settings, sentry_client)
