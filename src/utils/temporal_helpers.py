import re
import datetime

from dateutil.parser import parser

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

DATE_FORMAT = "%Y-%m-%d"

TIME_FORMAT = "%H:%M:%S"


def utc_now():
    return datetime.datetime.utcnow()


regex = re.compile(
    r'((?P<years>\d+?)y)?((?P<months>\d+?)m)?((?P<days>\d+?)d)?((?P<hours>\d+?)hr)?((?P<minutes>\d+?)min)?'
)


def to_timestamp(dt):
    return int(dt.replace(
        tzinfo=datetime.timezone.utc).timestamp())


def parse_datetime(value):
    return datetime.datetime.strptime(value, DATETIME_FORMAT)


def parse_time(value):
    return datetime.datetime.strptime(value, TIME_FORMAT)


def parse_date(value):
    return datetime.datetime.strptime(value, DATE_FORMAT)


def parse(_start_date):
    if type(_start_date) == datetime.datetime:
        return _start_date
    else:
        return parser.parse(_start_date)
