import motor.motor_asyncio as async_motor

from src.services.application import ApplicationService
from src.services.bearer_token_service import ErtisBearerTokenService
from src.services.events import EventService
from src.services.password_service import PasswordService
from src.services.role import RoleService
from src.services.user import UserService
from src.services.user_type import UserTypeService
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

        app.application_service = ApplicationService(app.db)
        app.bearer_token_service = ErtisBearerTokenService(app.db)
        app.password_service = PasswordService(app.db)
        app.role_service = RoleService(app.db)
        app.user_service = UserService(app.db)
        app.user_type_service = UserTypeService(app.db)
        app.event_service = EventService(app.db)

        app.persist_event = EventPersister(app.db)
