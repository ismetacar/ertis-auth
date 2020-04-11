import json

from sanic import response

from src.plugins.authorization import authorized
from src.resources.generic import ensure_membership_is_exists
from src.utils import query_helpers
from src.utils.json_helpers import bson_to_json


def init_events_api(app, settings):
    # region Get Event
    @app.route('/api/v1/memberships/<membership_id>/events/<event_id>', methods=['GET'])
    @authorized(app, settings, methods=['GET'])
    async def get_event(request, membership_id, event_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        resource = await app.event_service.get_event(event_id, membership_id)
        return response.json(json.loads(json.dumps(resource, default=bson_to_json)), 200)

    # endregion

    # region Query Events
    # noinspection DuplicatedCode
    @app.route('/api/v1/memberships/<membership_id>/events/_query', methods=['POST'])
    @authorized(app, settings, methods=['POST'])
    async def query_events(request, membership_id, *args, **kwargs):
        await ensure_membership_is_exists(app.db, membership_id, request.ctx.utilizer)
        where, select, limit, sort, skip = query_helpers.parse(request)
        events, count = await app.event_service.query_events(membership_id, where, select, limit, sort, skip)

        response_json = json.loads(json.dumps({
            'data': {
                'items': events,
                'count': count
            }
        }, default=bson_to_json))

        return response.json(response_json)

    # endregion
