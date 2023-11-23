# -*- coding: utf-8 -*-
import time
import uuid
import datetime


def generate_unique_number():
    unique_id = uuid.uuid4()
    unique_number = int(unique_id.int) & 0xffffffff
    return unique_number


def simple_retry(on_exception=None, max_attempts=3, delay_seconds=0.1):
    if on_exception and not callable(on_exception):
        raise ValueError("on_exception参数必须穿入一个callable对象")

    def _wrap(func):
        def _retry(*args, **kwargs):
            attempts = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if on_exception and not on_exception(e):
                        raise

                    if attempts >= max_attempts:
                        raise

                    time.sleep(delay_seconds)
                    attempts += 1
        return _retry
    return _wrap


def parse_dt(dt):
    if isinstance(dt, datetime.datetime):
        return dt
    elif isinstance(dt, str):
        if "." in dt:
            return datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f")
        else:
            return datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
    else:
        raise ValueError("invalid dt: %s" % dt)


def dt_to_milliseconds(dt):
    return int(dt.timestamp() * 1000 + dt.microsecond / 1000)


def milliseconds_to_dt(milliseconds):
    return datetime.datetime.fromtimestamp(milliseconds / 1000.)
