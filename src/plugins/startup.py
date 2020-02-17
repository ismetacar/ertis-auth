import motor.motor_asyncio as async_motor

from src.services.bearer_token_service import BlupointBearerTokenService
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

        app.bearer_token_service = BlupointBearerTokenService(app.db)
        app.persist_event = EventPersister(app.db)
