# -*- coding: utf-8 -*-

from quant_engine.scheduler.event import create_event_class, EventPriority, Event, _event_classes


def test_create_event_class():
    create_event_class("TestEvent1")
    assert "TestEvent1" in _event_classes
    e1 = _event_classes["TestEvent1"]()
    assert e1.__class__.__name__ == "TestEvent1"
    assert e1.priority == EventPriority.DEFAULT

    create_event_class("TestEvent2", priority=100)
    assert "TestEvent2" in _event_classes
    e2 = _event_classes["TestEvent2"]()
    assert e2.__class__.__name__ == "TestEvent2"
    assert e2.priority == 100

    assert isinstance(e1, Event)
    assert isinstance(e2, Event)
