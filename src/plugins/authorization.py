from functools import wraps

from src.resources.generic import ensure_token_is_not_revoked
from src.utils.errors import ErtisError
from src.utils.security_helpers import implies_any


def ensure_valid_token_provided(auth_header):
    try:
        token = auth_header.split(' ')[1]
        if auth_header.split(' ')[0] != 'Bearer':
            raise ErtisError(
                err_code="errors.authorizationError",
                err_msg="Invalid authorization header provided",
                status_code=401
            )
    except Exception as e:
        raise ErtisError(
            err_msg="Invalid authorization header provided",
            err_code="errors.authorizationError",
            status_code=401,
            reason=str(e)
        )

    return token


async def ensure_user_is_permitted(db, user, required_permission):
    user_role = await db.roles.find_one({
        'slug': user.get('role'),
        'membership_id': user.get('membership_id')
    })

    if not user_role:
        raise ErtisError(
            err_code="errors.permissionDenied",
            err_msg="Permission denied for this action <{}>".format(required_permission),
            status_code=403
        )

    user_permissions = user_role.get('permissions', [])
    has_permission = implies_any(user_permissions, required_permission)
    if not has_permission:
        raise ErtisError(
            err_code="errors.permissionDenied",
            err_msg="Permission denied for this action <{}>".format(required_permission),
            status_code=403
        )


def authorized(app, settings, methods=None, required_permission=None):
    if methods is None:
        methods = ['PATCH', 'PUT', 'POST', 'DELETE', 'GET']

    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            if request.method not in methods:
                response = await f(request, *args, **kwargs)
                return response
            auth_header = request.headers.get('authorization')
            token = ensure_valid_token_provided(auth_header)

            await ensure_token_is_not_revoked(app.db, token)

            user = await app.bearer_token_service.validate_token(token, settings['application_secret'], verify=True)

            if not user or user['decoded_token']['rf'] is True:
                raise ErtisError(
                    err_code="errors.authorizationError",
                    err_msg="Invalid authorization header provided",
                    status_code=401
                )

            if required_permission:
                await ensure_user_is_permitted(app.db, user, required_permission)

            kwargs['user'] = user
            request.ctx.user = user
            response = await f(request, *args, **kwargs)
            return response

        return decorated_function

    return decorator
