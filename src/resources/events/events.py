from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id


async def find_event(db, membership_id, event_id):
    event_doc = await db.events.find_one({
        '_id': maybe_object_id(event_id),
        'membership_id': membership_id
    })

    if not event_doc:
        raise ErtisError(
            err_code="errors.notFound",
            err_msg="Event not found by given id: <{}> in membership: <{}>".format(str(event_id), str(membership_id)),
            status_code=404
        )

    return event_doc
