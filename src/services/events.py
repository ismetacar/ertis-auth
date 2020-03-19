from src.resources.events.events import find_event
from src.resources.generic import query


class EventService(object):
    def __init__(self, db):
        self.db = db

    async def get_event(self, event_id, membership_id):
        return await find_event(self.db, membership_id, event_id)

    async def query_events(self, membership_id, where, select, limit, sort, skip):
        events, count = await query(self.db, membership_id, where, select, limit, skip, sort, 'events')
        return events, count
