# -*- coding: utf-8 -*-
import datetime

from ..common.exceptions import InternalError, InvalidCall


class Context(object):
    """
    Usage:
        上下文对象，方便各对象之间调用
    """

    _instance = None

    def __init__(self, task_name, event_bus, loop, scheduler, loader, debug, config, out, start=None, end=None):
        self._task_name = task_name
        self._event_bus = event_bus
        self._event_loop = loop
        self._scheduler = scheduler
        self._loader = loader
        self._debug = debug
        self._config = config
        self._out = out

        self._start = start or datetime.datetime.now()
        self._end = end

        self._account = None
        self._trade_gate = None
        self._portfolio = None
        self._strategy = None

        self._use_account = None

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
        """ 当前真实无力时间 """
        return self._event_loop.current_dt

    @property
    def strategy_dt(self):
        """ 策略中当前逻辑时间，每次处理某个事件时更新，用于方便了解处理到哪个事件了 """
        return self._event_loop.strategy_dt

    @property
    def account(self):
        if not self._use_account:
            raise InvalidCall("检测到use_account=False，程序未加载账户组件，无法调用账户模块相关API，"
                              "请在set_options中设置use_account=True后再试")
        return self._account

    @account.setter
    def account(self, acc):
        self._account = acc

    @property
    def trade_gate(self):
        if not self._use_account:
            raise InvalidCall("检测到use_account=False，程序未加载账户组件，无法调用账户模块相关API，"
                              "请在set_options中设置use_account=True后再试")

        return self._trade_gate

    @trade_gate.setter
    def trade_gate(self, gate):
        self._trade_gate = gate

    @property
    def portfolio(self):
        if not self._use_account:
            raise InvalidCall("检测到use_account=False，程序未加载账户组件，无法调用账户模块相关API，"
                              "请在set_options中设置use_account=True后再试")

        return self._portfolio

    @portfolio.setter
    def portfolio(self, p):
        self._portfolio = p

    @property
    def task_name(self):
        return self._task_name

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, s):
        self._strategy = s

    @property
    def config(self):
        return self._config

    @property
    def use_account(self):
        return self._use_account

    @use_account.setter
    def use_account(self, val):
        self._use_account = val

    @property
    def out(self):
        return self._out
