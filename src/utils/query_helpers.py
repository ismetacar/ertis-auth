import logging
from src.utils.errors import ErtisError


def parse_boolean(val, default=False):
    if not val:
        return False if not default else default

    if val in ['1', 'True', 'true']:
        return True
    else:
        return False


def get_skip(request):
    skip = request.args.get('skip', 0)
    return int(skip)


def get_limit(request, check_max_limit=True):
    max_limit = 1000
    limit = request.args.get('limit', None)
    if limit:
        if check_max_limit and int(limit) > max_limit:
            limit = max_limit
        return int(limit)


def get_select(request):
    try:
        _json = request.json.get("select", None)
        return _json
    except Exception as ex:
        logging.error(ex)
        raise ErtisError(
            err_code="errors.BadJsonGiven",
            err_msg="Body Json is Invalid",
            status_code=400
        )


def get_where(request):
    try:
        _json = request.json.get("where", None)
        return _json
    except Exception as ex:
        logging.error(ex)
        raise ErtisError(
            err_code="errors.BadJsonGiven",
            err_msg="Body Json is Invalid",
            status_code=400
        )


def get_sort(request):
    sort = None
    order_by = request.args.get('sort', None)
    if order_by:
        sort = []
        clauses = order_by.split(',')
        for clause in clauses:
            clause = clause.strip()
            if clause:
                if ' ' not in clause:
                    clause = clause + ' asc'
                sort.append(
                    (clause.split(' ')[0], -1 if clause.split(' ')[1] == 'desc' else 1))

    return sort


def parse_sort(order_by_str):
    sort = []
    clauses = order_by_str.split(',')
    for clause in clauses:
        clause = clause.strip()
        if clause:
            if ' ' not in clause:
                clause = clause + ' asc'
            sort.append(
                (clause.split(' ')[0], -1 if clause.split(' ')[1] == 'desc' else 1))

    return sort


def parse(request):
    where = get_where(request)
    select = get_select(request)
    limit = get_limit(request)
    sort = get_sort(request)
    skip = get_skip(request)
    return where, select, limit, sort, skip
