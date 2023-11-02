# -*- coding: utf-8 -*-
from collections import OrderedDict

from quant_engine.scheduler.bus import EventBus
from quant_engine.scheduler.event import Event


def test_init():
    bus = EventBus()
    assert not bus._subscribes
    assert bus._subscribes == OrderedDict()


class TestEvent1(Event):
    pass


class TestEvent2(Event):
    pass


def test_register():
    bus = EventBus()
    bus.register(TestEvent1, lambda e: 0, priority=0)
    bus.register(TestEvent1, lambda e: 1, priority=1)
    bus.register(TestEvent1, lambda e: -1, priority=-1)
    bus.register(TestEvent1, lambda e: -3, priority=-1)
    bus.register(TestEvent1, lambda e: -2, priority=-1)

    bus.register(TestEvent2, lambda e: 10, priority=0)
    bus.register(TestEvent2, lambda e: 11, priority=1)

    assert bus.emit(TestEvent1()) == [1, 0, -1, -3, -2]
    assert bus.emit(TestEvent2()) == [11, 10]


def test_unregister():
    bus = EventBus()

    def func(e):
        return -1
    bus.register(TestEvent1, lambda e: 0, priority=0)
    bus.register(TestEvent1, lambda e: 1, priority=1)
    bus.register(TestEvent1, func, priority=-1)

    bus.register(TestEvent2, lambda e: 10, priority=0)
    bus.register(TestEvent2, lambda e: 11, priority=1)

    bus.unregister(TestEvent1, func)
    assert bus.emit(TestEvent1()) == [1, 0]
    assert bus.emit(TestEvent2()) == [11, 10]
