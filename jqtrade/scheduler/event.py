# -*- coding: utf-8 -*-


class EventPriority:
    DAILY = DEFAULT = 0
    EVERY_MINUTE = 1
    ACCOUNT_SYNC = 2


class Event(object):
    """
    Usage:
        事件基类，所有事件类都要继承自此类
    """

    # 时间优先级，值越大优先级越高
    priority = EventPriority.DEFAULT

    def __repr__(self):
        return f'{self.__class__.__name__}(priority={self.priority})'


_event_classes = {}


def create_event_class(name, priority=EventPriority.DEFAULT):
    if name not in _event_classes:
        _event_classes[name] = type(name, (Event, ), {"priority": priority})
    return _event_classes[name]
