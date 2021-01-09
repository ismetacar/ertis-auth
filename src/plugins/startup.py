import motor.motor_asyncio as async_motor

from src.services.application_service import ApplicationService
from src.services.basic_token_service import ErtisBasicTokenService
from src.services.bearer_token_service import ErtisBearerTokenService
from src.services.event_service import EventService
from src.services.password_service import PasswordService
from src.services.provider_service import ProviderService
from src.services.role_service import RoleService
from src.services.user_service import UserService
from src.services.user_type_service import UserTypeService
from src.utils.events import EventPersister


def init_startup_methods(app, settings):
    @app.listener('before_server_start')
    async def register_mongo_db(app, loop):
        # Create a database connection pool
        connection_uri = settings['mongo_connection_string']
        database_name = settings['default_database']
        app.db = async_motor.AsyncIOMotorClient(
            connection_uri,
            maxIdleTimeMS=10000,
            minPoolSize=10,
            maxPoolSize=50,
            connectTimeoutMS=10000,
            retryWrites=True,
            waitQueueTimeoutMS=10000,
            serverSelectionTimeoutMS=10000
        )[database_name]

        app.bearer_token_service = ErtisBearerTokenService(app.db)
        app.basic_token_service = ErtisBasicTokenService(app.db)

        app.role_service = RoleService(app.db)
        app.application_service = ApplicationService(app.db, app.role_service)
        app.user_service = UserService(app.db, app.role_service)
        app.password_service = PasswordService(app.db, app.user_service)
        app.user_type_service = UserTypeService(app.db)

        app.event_service = EventService(app.db)
        app.persist_event = EventPersister(app.db)
        app.provider_service = ProviderService(app.db, app.user_type_service, app.user_service, app.persist_event)
