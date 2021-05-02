import json

from sanic import response
from sanic_openapi import doc

from src.resources.generic import ensure_membership_is_exists
from src.resources.providers.facebook import validate_with_facebook
from src.resources.providers.google import validate_with_google
from src.utils.errors import ErtisError
from src.utils.json_helpers import bson_to_json

VALIDATION_LOOKUP = {
    'google': validate_with_google,
    'facebook': validate_with_facebook
}


def init_provider_sign_in_api(app, settings):
    @app.route('/api/v1/sign-up/<provider_slug>')
    @doc.tag("Social Login")
    @doc.operation("Login")
    async def sign_in_with(request, provider_slug, *args, **kwargs):
        membership_id = request.headers.get('x-ertis-alias', None)
        membership = await ensure_membership_is_exists(app.db, membership_id, user=None)
        token = request.args.get('id_token')

        exists_provider = await app.provider_service.get_provider_by_slug(provider_slug, str(membership['_id']))

        validation_method = VALIDATION_LOOKUP.get(exists_provider['type'], None)
        if not validation_method:
            raise ErtisError(
                err_code="Provider not in provider validation lookup",
                err_msg="errors.providerNotExists",
                status_code=400
            )

        user = validation_method(token, settings, str(membership['_id']))
        exists_user = await app.provider_service.check_user(user)
        if exists_user:
            affected_user = await app.provider_service.update_user(exists_user, exists_provider, token, user)
        else:
            affected_user = await app.provider_service.create_user(user, exists_provider, token)

        token = await app.bearer_token_service.generate_token(
            settings,
            membership,
            affected_user,
            app.persist_event,
            skip_auth=True
        )

        return response.json(json.loads(json.dumps(token, default=bson_to_json)), 201)
