import enum
from functools import wraps

from src.resources.generic import ensure_token_is_not_revoked
from src.utils.errors import ErtisError
from src.utils.security_helpers import implies_any


class TokenTypes(enum.Enum):
    BEARER = 0
    BASIC = 1


def get_token_string(auth_header):
    token = auth_header.split(' ')[1]
    return token


async def ensure_utilizer_is_permitted(db, utilizer, required_permission):
    role = await db.roles.find_one({
        'slug': utilizer.get('role'),
        'membership_id': utilizer.get('membership_id')
    })

    if not role:
        raise ErtisError(
            err_code="errors.permissionDenied",
            err_msg="Permission denied for this action <{}>".format(required_permission),
            status_code=403
        )

    permissions = role.get('permissions', [])
    has_permission = implies_any(permissions, required_permission)
    if not has_permission:
        raise ErtisError(
            err_code="errors.permissionDenied",
            err_msg="Permission denied for this action <{}>".format(required_permission),
            status_code=403
        )


def authorized(app, settings, methods=None, required_permission=None, allowed_token_types=None):
    if not allowed_token_types:
        allowed_token_types = [TokenTypes.BASIC, TokenTypes.BEARER]

    if methods is None:
        methods = ['PATCH', 'PUT', 'POST', 'DELETE', 'GET']

    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            if request.method not in methods:
                response = await f(request, *args, **kwargs)
                return response
            auth_header = request.headers.get('authorization')
            if auth_header.startswith('Bearer '):
                token_type = TokenTypes.BEARER
            elif auth_header.startswith('Basic '):
                token_type = TokenTypes.BASIC
            else:
                raise ErtisError(
                    err_code="errors.invalidAuthHeader",
                    err_msg="Auth type not supported. Auth type must be starts with one of Bearer or Basic",
                    status_code=401
                )

            token = get_token_string(auth_header)

            if token_type not in allowed_token_types:
                raise ErtisError(
                    err_code="errors.disallowedAuthTypeProvidedInHeader",
                    err_msg="This operation disallowed for auth type: <{}>".format(token_type.name),
                    status_code=403
                )

            if token_type == TokenTypes.BEARER:
                await ensure_token_is_not_revoked(app.db, token)
                user = await app.bearer_token_service.validate_token(token, settings['application_secret'], verify=True)
                if not user or user['decoded_token']['rf'] is True:
                    raise ErtisError(
                        err_code="errors.authorizationError",
                        err_msg="Invalid authorization header provided",
                        status_code=401
                    )
                utilizer = user

            elif token_type == TokenTypes.BASIC:
                application = await app.basic_token_service.validate_token(token)
                utilizer = application

            else:
                raise ErtisError(
                    err_code="errors.invalidAuthHeader",
                    err_msg="Auth type not supported. Auth type must be starts with one of Bearer or Basic",
                    status_code=401
                )

            if required_permission:
                await ensure_utilizer_is_permitted(app.db, utilizer, required_permission)

            kwargs['utilizer'] = utilizer
            request.ctx.utilizer = utilizer
            response = await f(request, *args, **kwargs)
            return response

        return decorated_function

    return decorator
