# -*- coding: utf-8 -*-
import datetime

from .exceptions import InternalError


class Context(object):
    """ 上下文对象，方便各对象之间调用 """

    _instance = None

    def __init__(self, event_bus, loop, scheduler, loader, debug, start=None, end=None):
        self._event_bus = event_bus
        self._event_loop = loop
        self._scheduler = scheduler
        self._loader = loader
        self._debug = debug

        self._start = start or datetime.datetime.now()
        self._end = end

        self.__class__._instance = self

    @property
    def event_bus(self):
        return self._event_bus

    @property
    def event_loop(self):
        return self._event_loop

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def loader(self):
        return self._loader

    @property
    def debug(self):
        return self._debug

    @property
    def loop(self):
        return self._event_loop

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            raise InternalError("Context not initialized")
        return cls._instance

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def current_dt(self):
        """ 当前真实时间 """
        return self._event_loop.current_dt

    @property
    def strategy_dt(self):
        """ 策略中当前逻辑事件，每次处理某个事件时更新，用于方便了解处理到哪个事件了 """
        return self._event_loop.strategy_dt
