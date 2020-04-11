from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id


class ErtisBasicTokenService(object):
    def __init__(self, db):
        self.db = db

    async def validate_token(self, token):
        try:
            split_token = token.split(':')
            application_id = split_token[0]
            application_secret = split_token[1]

        except Exception as e:
            raise ErtisError(
                err_msg="Provided basic token is invalid.",
                err_code="errors.invalidBasicTokenProvided",
                status_code=400
            )

        application = await self.get_application(application_id)
        exists_secret = application['secret']
        if application_secret != exists_secret:
            raise ErtisError(
                err_msg="Application secrets mismatch.",
                err_code="errors.applicationSecretMismatch",
                status_code=401
            )

        return application

    async def get_application(self, application_id):
        application = await self.db.applications.find_one({
            '_id': maybe_object_id(application_id)
        })

        if not application:
            raise ErtisError(
                err_code="errors.applicationNotFound",
                err_msg="Application was not found in db by given id: <{}>".format(str(application_id)),
                status_code=404
            )

        return application