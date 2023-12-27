# -*- coding: utf-8 -*-
import pytest
import datetime

from jqtrade.scheduler.event_source import EventSource, EventSourceScheduler, TimeExprParser
from jqtrade.scheduler.event import Event
from jqtrade.scheduler.config import get_config


config = get_config()


def test_event_source_init():
    es = EventSource()
    assert es._daily == []
    assert es._events == []
    assert es._days == []
    assert es._event_changed_callback == []
    assert es._need_regenerate_events


def test_reset_events():
    es = EventSource()
    assert es._need_regenerate_events

    es.setup()

    assert not es._need_regenerate_events
    es._reset_events_if_needed()

    assert es._daily == []
    assert es._events == []

    assert len(es._days)


def test_get_days():
    es = EventSource()
    es.setup()

    days = es._get_days(count=2)

    today = datetime.date.today()
    assert days == [today, today + datetime.timedelta(days=1)]


def test_daily():
    es = EventSource()
    es.setup()

    assert es._daily == []

    es.daily(Event, "09:30:00")
    es.daily(Event, "every_minute")
    es.daily(Event, "open-30")
    es.daily(Event, "close-30")
    assert es._daily == [
        ("09:30:00", Event),
        ("every_minute", Event),
        ("open-30", Event),
        ("close-30", Event)
    ]
    assert es._need_regenerate_events


class TestEvent1(Event):
    pass


class TestEvent2(Event):
    pass


class TestEvent3(Event):
    pass


class TestEvent4(Event):
    pass


class TestEvent5(Event):
    pass


class TestEvent6(Event):
    pass


@pytest.fixture()
def context():
    from jqtrade.scheduler.strategy import Strategy
    from jqtrade.scheduler.context import Context
    from jqtrade.scheduler.bus import EventBus
    from jqtrade.scheduler.loop import EventLoop
    from jqtrade.scheduler.loader import Loader
    from jqtrade.scheduler.event_source import EventSourceScheduler
    ctx = Context("test", EventBus(), EventLoop(), EventSourceScheduler(), Loader("../demo/demo.py"), False, None, None)
    strategy = Strategy(ctx)


def test_gen_events(context):
    today = datetime.date.today()
    old_cfg = bool(config.ENABLE_HISTORY_START)

    try:
        config.ENABLE_HISTORY_START = True
        es = EventSource(datetime.datetime.combine(today, datetime.time(8, 0)))
        es.setup()

        es.daily(TestEvent1, "09:30:00")
        es.daily(TestEvent2, "open")
        es.daily(TestEvent3, "open-30m")
        es.daily(TestEvent4, "14:30:00")
        es.daily(TestEvent5, "close-30m")
        es.daily(TestEvent6, "close")

        assert not es._events

        es.gen_events()
    finally:
        config.ENABLE_HISTORY_START = old_cfg

    # open-30m
    assert es._events[0][0] == datetime.datetime.combine(today, datetime.time(9, 0))
    assert isinstance(es._events[0][1], TestEvent3)

    # 09:30
    assert es._events[1][0] == datetime.datetime.combine(today, datetime.time(9, 30))
    assert isinstance(es._events[1][1], TestEvent1)

    # open
    assert es._events[2][0] == datetime.datetime.combine(today, datetime.time(9, 30))
    assert isinstance(es._events[2][1], TestEvent2)

    # 14:30
    assert es._events[3][0] == datetime.datetime.combine(today, datetime.time(14, 30))
    assert isinstance(es._events[3][1], TestEvent4)

    # close-30m
    assert es._events[4][0] == datetime.datetime.combine(today, datetime.time(14, 30))
    assert isinstance(es._events[4][1], TestEvent5)

    # close
    assert es._events[5][0] == datetime.datetime.combine(today, datetime.time(15, 0))
    assert isinstance(es._events[5][1], TestEvent6)


def test_start():
    old_cfg = bool(config.ENABLE_HISTORY_START)

    try:
        config.ENABLE_HISTORY_START = True

        es = EventSource(datetime.datetime(2023, 6, 4, 10, 0, 0))
        es.setup()

        assert es._start == datetime.datetime(2023, 6, 4, 10, 0, 0)
        assert es._end is None

        es.daily(TestEvent1, "09:30:00")
        es.daily(TestEvent2, "10:00:00")
        es.gen_events()

        e1 = es.get_next_event()
        assert e1[0] == datetime.datetime(2023, 6, 4, 10, 0, 0)
        assert isinstance(e1[1], TestEvent2)

        e2 = es.get_next_event()
        assert e2[0] == datetime.datetime(2023, 6, 5, 9, 30, 0)
        assert isinstance(e2[1], TestEvent1)

        e3 = es.get_next_event()
        assert e3[0] == datetime.datetime(2023, 6, 5, 10, 0, 0)
        assert isinstance(e3[1], TestEvent2)

        e4 = es.peek_next_event()
        assert e4[0] == datetime.datetime(2023, 6, 6, 9, 30, 0)
        assert isinstance(e4[1], TestEvent1)

        e5 = es.peek_next_event()
        assert e5[0] == datetime.datetime(2023, 6, 6, 9, 30, 0)
        assert isinstance(e5[1], TestEvent1)

    finally:
        config.ENABLE_HISTORY_START = old_cfg

    try:
        config.ENABLE_HISTORY_START = False

        now = datetime.datetime.now()
        dt1 = (now + datetime.timedelta(minutes=10)).replace(microsecond=0)
        dt2 = (now + datetime.timedelta(minutes=20)).replace(microsecond=0)

        es = EventSource(datetime.datetime(2023, 6, 4, 10, 0, 0))
        es.setup()

        assert es._start >= now

        es.daily(TestEvent1, dt1.strftime("%H:%M:%S"))
        es.daily(TestEvent2, dt2.strftime("%H:%M:%S"))
        es.gen_events()

        e1 = es.get_next_event()
        assert e1[0] == dt1
        assert isinstance(e1[1], TestEvent1)

        e2 = es.get_next_event()
        assert e2[0] == dt2
        assert isinstance(e2[1], TestEvent2)

        e3 = es.get_next_event()
        assert e3[0] == datetime.datetime.combine(dt1.date() + datetime.timedelta(days=1), dt1.time())
        assert isinstance(e3[1], TestEvent1)

        e4 = es.get_next_event()
        assert e4[0] == datetime.datetime.combine(dt2.date() + datetime.timedelta(days=1), dt2.time())
        assert isinstance(e4[1], TestEvent2)

    finally:
        config.ENABLE_HISTORY_START = old_cfg


def test_end():
    old_cfg = bool(config.ENABLE_HISTORY_START)

    try:
        config.ENABLE_HISTORY_START = True

        es = EventSource(start=datetime.datetime(2023, 6, 4, 10, 0, 0), end=datetime.datetime(2023, 6, 5, 10, 0, 0))
        es.setup()

        assert es._start == datetime.datetime(2023, 6, 4, 10, 0, 0)
        assert es._end == datetime.datetime(2023, 6, 5, 10, 0, 0)

        es.daily(TestEvent1, "09:30:00")
        es.daily(TestEvent2, "10:00:00")
        es.daily(TestEvent3, "10:00:01")
        es.gen_events()

        e1 = es.get_next_event()
        assert e1[0] == datetime.datetime(2023, 6, 4, 10, 0, 0)
        assert isinstance(e1[1], TestEvent2)

        e2 = es.get_next_event()
        assert e2[0] == datetime.datetime(2023, 6, 4, 10, 0, 1)
        assert isinstance(e2[1], TestEvent3)

        e3 = es.get_next_event()
        assert e3[0] == datetime.datetime(2023, 6, 5, 9, 30, 0)
        assert isinstance(e3[1], TestEvent1)

        e4 = es.get_next_event()
        assert e4[0] == datetime.datetime(2023, 6, 5, 10, 0, 0)
        assert isinstance(e4[1], TestEvent2)

        assert es.get_next_event() is None
        assert es.peek_next_event() is None

    finally:
        config.ENABLE_HISTORY_START = old_cfg

    try:
        config.ENABLE_HISTORY_START = False

        now = datetime.datetime.now()
        dt1 = (now + datetime.timedelta(minutes=10)).replace(microsecond=0)
        dt2 = (now + datetime.timedelta(minutes=20)).replace(microsecond=0)

        es = EventSource(datetime.datetime(2023, 6, 4, 10, 0, 0))
        es.setup()

        assert es._start >= now

        es.daily(TestEvent1, dt1.strftime("%H:%M:%S"))
        es.daily(TestEvent2, dt2.strftime("%H:%M:%S"))
        es.gen_events()

        e1 = es.get_next_event()
        assert e1[0] == dt1
        assert isinstance(e1[1], TestEvent1)

        e2 = es.get_next_event()
        assert e2[0] == dt2
        assert isinstance(e2[1], TestEvent2)

        e3 = es.get_next_event()
        assert e3[0] == datetime.datetime.combine(dt1.date() + datetime.timedelta(days=1), dt1.time())
        assert isinstance(e3[1], TestEvent1)

        e4 = es.get_next_event()
        assert e4[0] == datetime.datetime.combine(dt2.date() + datetime.timedelta(days=1), dt2.time())
        assert isinstance(e4[1], TestEvent2)

    finally:
        config.ENABLE_HISTORY_START = old_cfg
