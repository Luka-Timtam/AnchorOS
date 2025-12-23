"""
Fixed timezone configuration for AnchorOS.
All datetime operations use Pacific/Auckland timezone.
No automatic timezone detection or introspection.
"""

import os
from datetime import datetime, date, timedelta, timezone as tz

TIMEZONE_NAME = 'Pacific/Auckland'
TIMEZONE_OFFSET_HOURS = 13
TIMEZONE_OFFSET_DST_HOURS = 12

_FIXED_OFFSET = tz(timedelta(hours=TIMEZONE_OFFSET_HOURS))

os.environ['TZ'] = TIMEZONE_NAME

def get_timezone():
    return _FIXED_OFFSET

def now():
    return datetime.now(_FIXED_OFFSET)

def today():
    return now().date()

def now_iso():
    return now().isoformat()

def now_date_iso():
    return today().isoformat()

def start_of_day(d=None):
    if d is None:
        d = today()
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_FIXED_OFFSET)

def end_of_day(d=None):
    if d is None:
        d = today()
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=_FIXED_OFFSET)

def start_of_week(d=None):
    if d is None:
        d = today()
    days_since_monday = d.weekday()
    return d - timedelta(days=days_since_monday)

def start_of_month(d=None):
    if d is None:
        d = today()
    return date(d.year, d.month, 1)

def parse_datetime_to_local(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=_FIXED_OFFSET)
        return value
    if isinstance(value, str):
        try:
            if 'T' in value:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=_FIXED_OFFSET)
                return dt
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=_FIXED_OFFSET)
        except:
            return None
    return None

def parse_date_only(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.split('T')[0])
        except:
            return None
    return None

def format_datetime(dt, fmt='%Y-%m-%d %H:%M'):
    if dt is None:
        return ''
    if isinstance(dt, str):
        dt = parse_datetime_to_local(dt)
    if dt is None:
        return ''
    return dt.strftime(fmt)

def format_date(d, fmt='%Y-%m-%d'):
    if d is None:
        return ''
    if isinstance(d, str):
        d = parse_date_only(d)
    if d is None:
        return ''
    return d.strftime(fmt)

def days_ago(n):
    return today() - timedelta(days=n)

def days_from_now(n):
    return today() + timedelta(days=n)
