# -*- coding: utf-8 -*-
from collections import OrderedDict

from ..common.log import sys_logger


logger = sys_logger.getChild("bus")


class EventBus(object):
    """
    Usage:
        1. 给事件绑定注册回调函数，并维护绑定关系和回调优先级
        2. 触发事件已绑定的回调函数
    """

    def __init__(self):
        self._subscribes = OrderedDict()

    def register(self, event_cls, callback, priority=0):
        """ 注册事件类的回调函数

        Args:
            event_cls: .event.Event子类
            callback: 回调函数
                函数签名：func(event) -> None
            priority: 回调函数优先级，值越大越先调用
        """
        logger.debug(f"register callback: {callback.__name__}, event_cls: {event_cls}, priority: {priority}")
        self._subscribes.setdefault(event_cls, {}).setdefault(priority, []).append(callback)

    def unregister(self, event_cls, callback):
        """ 取消注册事件类的某个回调函数

        Args:
            event_cls: scheduler.event.Event的子类
            callback: 回调函数对象
        """
        logger.debug(f"unregister callback: {callback.__name__}, event_cls: {event_cls}")
        event_subscribes = self._subscribes.get(event_cls, {})
        for _priority in event_subscribes:
            try:
                event_subscribes[_priority].remove(callback)
            except ValueError:
                logger.error(f"already unregister callback: {callback.__name__} of event_cls: {event_cls}")

    def emit(self, event):
        """ 触发事件绑定的回调函数

        Args:
            event: event_class实例
        """
        ret = []
        for _event_cls in self._subscribes:
            if not isinstance(event, _event_cls):
                continue
            _event_subscribes = self._subscribes.get(_event_cls, {})
            for _priority in sorted(_event_subscribes, reverse=True):
                for _callback in _event_subscribes[_priority]:
                    logger.debug(f"emit event: {event}, callback: {_callback.__name__}")
                    ret.append(_callback(event))
        return ret
