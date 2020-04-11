import asyncio
import datetime
import json
import logging

from bson import ObjectId

from src.utils.errors import ErtisError
from src.utils.json_helpers import bson_to_json, object_hook, maybe_object_id

logger = logging.getLogger("events")

__HANDLERS = {}

__GLOBAL_HANDLERS = []


class Event(object):
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


async def dispatch(event):
    _e_type = event.type

    for g_handler in __GLOBAL_HANDLERS:
        logger.info("Handler<{}> runned for event<{}>".format(g_handler.__name__, type(event).__name__))

        await asyncio.ensure_future(g_handler(event))

    if _e_type not in __HANDLERS:
        return

    for handler in __HANDLERS[_e_type]:
        logger.info("Handler<{}> runned for event<{}>".format(
            handler.__class__.__name__, event.type
        ))

        try:
            await handler.handle(event)
        except Exception as e:
            logging.exception("Exception occured while running event handler... <{}>".format(str(e)))
            continue


def subscribe_g(f):
    __GLOBAL_HANDLERS.append(f)


def subscribe(handler):
    for event_name in handler.event_names:

        if event_name not in __HANDLERS:
            __HANDLERS[event_name] = []

        if not hasattr(handler, 'handle'):
            raise ErtisError(
                err_msg="Handler objects must implement handle method",
                err_code="errors.internalError"
            )

        __HANDLERS[event_name].append(handler)

        logger.info(
            "Function<{}> subscribed event<{}>.".format(handler.__class__.__name__, event_name)
        )


def subscribe_global(f):
    global __HANDLERS
    __HANDLERS[None].append(f)


class EventPersister(object):
    def __init__(self, db):
        self.db = db

    async def on_event(self, event):
        data = {
            "_id": getattr(event, '_id', ObjectId()),
            "type": event.type,
            "document": getattr(event, 'document'),
            "prior": getattr(event, 'prior'),
            "utilizer": getattr(event, 'utilizer'),
            "membership_id": getattr(event, 'membership_id', None),
            "custom": getattr(event, 'custom', None),
            "sys": {
                "created_at": datetime.datetime.utcnow(),
                "created_by": getattr(event, 'utilizer').get('username', getattr(event, 'utilizer').get('name'))
            }
        }

        dumped = json.loads(json.dumps(data, default=bson_to_json), object_hook=object_hook)

        dumped['_id'] = maybe_object_id(dumped['_id'])

        await self.db.events.insert_one(dumped)

        logger.info("Persisted event <{}>.".format(event.type))
