from datetime import datetime

# python timezone
import pytz


def utc_now():
    return datetime.now().replace(tzinfo=pytz.utc)