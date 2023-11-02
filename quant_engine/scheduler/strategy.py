# -*- coding: utf-8 -*-
import datetime

from .event_source import EventSource
from .exceptions import InvalidCall, InvalidParam
from .event import create_event_class, EventPriority
from .log import user_logger, sys_logger
from .user_api import UserContext
from .config import get_config

config = get_config()


logger = sys_logger.getChild("strategy")


class Strategy(object):
    """ 策略管理类

        1. 初始化策略运行环境以及依赖的API
        2. 初始化事件循环所需的event_source
        3. 启动进程后，触发执行 process_initialize
    """

    TIME_DICT = {
        'open': 'open+0m',
        'close': 'close+0m',
        'before_open': 'open-30m',
        'after_close': 'close+30m',
    }

    def __init__(self, ctx):
        self._ctx = ctx

        self._user_module = ctx.loader.load()

        self._user_ctx = UserContext(self._ctx)

        self._schedules = []

        self._is_scheduler_allowed = False

        self._schedule_count = 0

    def setup(self):
        logger.debug("strategy setup")
        self.make_apis()

        if hasattr(self._user_module, "process_initialize"):
            # 只允许在process_initialize中调用run_daily设置每日定时任务
            self._is_scheduler_allowed = True
            logger.debug("call user process_initialize")
            self._user_module.process_initialize(self._user_ctx)
            self._is_scheduler_allowed = False

        self.schedule()

    def make_apis(self):
        # todo: 补充其他模块的API
        self._user_module.run_daily = self.run_daily
        self._user_module.log = user_logger
        self._user_module.context = self._user_ctx

    def wrap_user_callback(self, callback):
        def _callback(event):
            return callback(self._user_ctx)
        return _callback

    def schedule(self):
        for _desc in self._schedules:
            logger.info("schedule user daily task: %s" % _desc)

            _callback = self._get_handle(_desc['name'])
            _cls_name = 'Scheduler_{}_{}'.format(_desc['name'], self._schedule_count)

            event_source = EventSource(start=self._ctx.start, end=self._ctx.end)
            event_source.setup()
            if _desc['time'] == "every_minute":
                event_cls = create_event_class(_cls_name, priority=EventPriority.EVERY_MINUTE)
                _today = datetime.date.today()
                for _start, _end in config.MARKET_PERIOD:
                    _start_dt = datetime.datetime.combine(_today, _start)
                    _end_dt = datetime.datetime.combine(_today, _end)
                    _current_dt = _start_dt
                    while _current_dt <= _end_dt:
                        event_source.daily(event_cls, _current_dt.strftime("%H:%M:%S"))
                        _current_dt += datetime.timedelta(minutes=1)
            else:
                event_cls = create_event_class(_cls_name)
                event_source.daily(event_cls, _desc["time"])

            self._ctx.event_bus.register(event_cls, self.wrap_user_callback(_callback))
            self._ctx.scheduler.schedule(event_source)

            self._schedule_count += 1

    def run_daily(self, func, time):
        logger.debug("strategy call run_daily. func=%s, time=%s" % (func, time))
        if not self._is_scheduler_allowed:
            raise InvalidCall('Function `run_daily` only valid in `process_initialize`')

        time = self.TIME_DICT.get(time) or time

        module, func = self._check_handle(func)

        desc = {
            'module': module,
            'name': func,
            'time': time,
        }
        self._schedules.append(desc)

    @staticmethod
    def _check_handle(func):
        if not callable(func):
            raise InvalidParam("user `{}` is not callable".format(func))
        return func.__module__, func.__name__

    def _get_handle(self, func_name):
        return getattr(self._user_module, func_name, None)

    @property
    def user_module(self):
        return self._user_module
