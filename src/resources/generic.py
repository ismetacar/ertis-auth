import enum

from pymongo.errors import OperationFailure

from src.utils.errors import ErtisError
from src.utils.json_helpers import maybe_object_id


class OperationTypes(enum.Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


QUERY_BODY_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'where': {
            'type': 'object'
        },
        'select': {
            'type': 'object'
        }
    }
}


def normalize_ids(where):
    if not where:
        return {}

    if '_id' in where:
        if type(where['_id']) == dict and "$in" in where['_id']:
            _ids = [
                maybe_object_id(_id)
                for _id in where['_id']['$in']
            ]
            where['_id']['$in'] = _ids
            return where
        elif type(where['_id']) == str:
            where['_id'] = maybe_object_id(where['_id'])
            return where
    return where


def _pre_process_where(where):
    normalized_where = normalize_ids(where)
    return normalized_where


async def query(db, membership_id=None, where=None, select=None, limit=None, sort=None, skip=None, collection=None):
    try:
        where = _pre_process_where(where)
        if not membership_id:
            raise ErtisError(
                err_msg="membership_id not passed to query",
                err_code="errors.internalServerError",
                status_code=500
            )
            
        where.update({
            'membership_id': membership_id
        })

        if not select:
            select = None

        if not limit or limit > 500:
            limit = 200

        cursor = db[collection].find(where, select)

        total_count = await cursor.explain()

        if skip:
            cursor.skip(int(skip))

        if limit:
            cursor.limit(int(limit))

        if sort:
            cursor.sort(sort)

        items = await cursor.to_list(None)

        return items, total_count["executionStats"]["nReturned"]

    except OperationFailure as e:
        if e.code in [2, 4]:
            raise ErtisError(
                context=e.details,
                err_msg='Please provide valid query...',
                err_code='errors.badQuery',
                status_code=400
            )

        raise


async def ensure_token_is_not_revoked(db, token):
    revoked_token = await db.revoked_tokens.find_one({
        'token': token
    })
    if revoked_token:
        raise ErtisError(
            err_code="errors.providedTokenWasRevokedBefore",
            err_msg="Provided token was revoked before",
            status_code=401
        )


async def ensure_membership_is_exists(db, membership_id, user=None):
    membership = await db.memberships.find_one({
        '_id': maybe_object_id(membership_id)
    })

    if not membership:
        raise ErtisError(
            err_msg="Membership not found in db by given membership_id: <{}>".format(membership_id),
            err_code="errors.MembershipNotFound",
            status_code=404
        )

    if user and str(user['membership_id']) != membership_id:
        raise ErtisError(
            err_code="errors.userNotPermittedForMembership",
            err_msg="User is not permitted for membership: <{}>".format(membership_id),
            status_code=401
        )

    return membership