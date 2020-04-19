from src.utils.errors import ErtisError


def validate_with_facebook(token, settings, membership_id):
    raise ErtisError(
        err_msg="Facebook login not implemented yet",
        err_code="errors.notImplemented",
        status_code=501
    )
