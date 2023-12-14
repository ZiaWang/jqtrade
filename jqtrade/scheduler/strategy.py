# -*- coding: utf-8 -*-
import os
import datetime

from importlib import import_module

from ..common.exceptions import InvalidCall, InvalidParam, TaskError, ConfigError
from ..common.log import user_logger, sys_logger
from ..common.utils import parse_time

from .event_source import EventSource
from .event import create_event_class, EventPriority
from .api import UserContext, strategy_print
from .config import get_config

config = get_config()


logger = sys_logger.getChild("strategy")


class Strategy(object):
    """ 策略管理类

    Usage:
        1. 初始化策略运行环境以及依赖的API
        2. 初始化事件循环所需的event_source
        3. 启动进程后，触发执行 process_initialize
        4. 加载并初始化account模块

        支持的set_options选项：
            "use_account": bool, 策略是否使用account模块，不启用account模块时，仅可用于运行定时任务
            "runtime_dir": str，设置策略进程运行时目录，默认为 "~/jqtrade"
            "market_period": list of tuple，默认：
                [
                    (datetime.time(9, 30), datetime.time(11, 30)),
                    (datetime.time(13, 0), datetime.time(15, 0)),
                ]
    """

    TIME_DICT = {
        'open': 'open+0m',
        'close': 'close+0m',
        'before_open': 'open-30m',
        'after_close': 'close+30m',
    }

    def __init__(self, ctx):
        self._ctx = ctx
        ctx.strategy = self

        self._user_module = ctx.loader.load()

        self._user_ctx = UserContext(self._ctx)

        self._schedules = []

        self._is_scheduler_allowed = False

        self._schedule_count = 0

        self._options = {}

    def setup(self):
        logger.info("setup strategy")
        self.make_apis()

        if hasattr(self._user_module, "process_initialize"):
            # 只允许在process_initialize中调用run_daily设置每日定时任务
            self._is_scheduler_allowed = True
            logger.info("执行用户process_initialize函数")
            self._user_module.process_initialize(self._user_ctx)
            self._is_scheduler_allowed = False
        else:
            raise TaskError("策略代码中未定义process_initialize函数")

        self.schedule()

    def make_apis(self):
        # 调度模块相关API
        self._user_module.run_daily = self.run_daily
        self._user_module.log = user_logger
        self._user_module.context = self._user_ctx
        self._user_module.set_options = self.set_options
        self._user_module.print = strategy_print

        # account模块相关API
        if config.SETUP_ACCOUNT:
            from ..account import api as account_api
            for _name in account_api.__all__:
                setattr(self._user_module, _name, getattr(account_api, _name))

    def wrap_user_callback(self, callback):
        def _callback(event):
            return callback(self._user_ctx)
        return _callback

    def schedule(self):
        for _desc in self._schedules:
            logger.info(f"设置定时任务: {_desc}")

            _callback = self._get_handle(_desc['name'])
            _cls_name = f"Scheduler_{_desc['name']}_{self._schedule_count}"

            event_source = EventSource(start=self._ctx.start, end=self._ctx.end)
            event_source.setup()
            if _desc['time'] == "every_minute":
                event_cls = create_event_class(_cls_name, priority=EventPriority.EVERY_MINUTE)
                _today = datetime.date.today()

                market_period = self._options.get("market_period", config.MARKET_PERIOD)
                for _period in market_period:
                    if len(_period) != 2:
                        raise ValueError(f"market period设置错误：{_period}")
                    _start, _end = _period
                    if not (isinstance(_start, datetime.time) and isinstance(_end, datetime.time)):
                        raise ValueError("market period设置的时间类型错误，需要是datetime.time类型。")
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
        logger.info(f"run_daily. func={func.__name__}, time={time}")
        if not self._is_scheduler_allowed:
            raise InvalidCall('run_daily函数只允许在process_initialize中调用')

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
            raise InvalidParam(f"{func} is not callable")
        return func.__module__, func.__name__

    def _get_handle(self, func_name):
        return getattr(self._user_module, func_name, None)

    @property
    def user_module(self):
        return self._user_module

    def set_options(self, **kwargs):
        if not self._is_scheduler_allowed:
            raise InvalidCall("set_options只能在process_initialize中调用")

        # parse scheduler options
        if "use_account" in kwargs:
            kwargs["use_account"] = bool(kwargs["use_account"])

        market_period = kwargs.get("market_period")
        if market_period:
            periods = []
            for _period in market_period:
                if len(_period) != 2:
                    raise ValueError(f"market_period设置错误：{_period}")
                _start, _end = _period
                periods.append((parse_time(_start), parse_time(_end)))
            kwargs["market_period"] = periods

        # parse account options
        if "sync_balance" in kwargs:
            kwargs["sync_balance"] = bool(kwargs["sync_balance"])

        if "sync_order" in kwargs:
            kwargs["sync_order"] = bool(kwargs["sync_order"])

        if "sync_internal" in kwargs:
            kwargs["sync_internal"] = float(kwargs["sync_internal"])

        sync_period = kwargs.get("sync_period")
        if sync_period:
            periods = []
            for _period in sync_period:
                if len(_period) != 2:
                    raise ValueError(f"sync_period设置错误：{_period}")
                _start, _end = _period
                periods.append((parse_time(_start), parse_time(_end)))
            kwargs["sync_period"] = periods

        # set options
        self._options = kwargs

        # set_options 后需要立即执行的初始化工作，避免用户查询到未同步的account信息
        runtime_dir = os.path.abspath(os.path.expanduser(kwargs.get("runtime_dir", config.RUNTIME_DIR)))
        if not os.path.isdir(runtime_dir):
            os.makedirs(runtime_dir)
        logger.info(f"程序运行时目录：{runtime_dir}")

        self._ctx.use_account = use_account = kwargs.get("use_account", config.SETUP_ACCOUNT)
        if use_account:
            self.setup_account(kwargs)
        else:
            logger.warn("检测到use_account设置为False，策略进程将不再加载账户模块组件，调用账户相关API可能会报错")

    def setup_account(self, options):
        logger.info("加载account模块")

        if "account_no" not in options:
            raise InvalidParam("set_options必须通过'account_no'选项设置资金账号")

        from ..account.account import Account
        from ..account.portfolio import Portfolio
        from ..account.config import setup_account_config, get_config as get_account_config
        if self._ctx.config:
            logger.info(f"account模块加载用户自定义配置：{self._ctx.config}")
            setup_account_config(self._ctx.config)
        account_config = get_account_config()
        if not account_config.TRADE_GATE:
            raise ConfigError("未配置trade gate")

        try:
            module_name, gate_name = account_config.TRADE_GATE.rsplit(".", 1)
            module = import_module(module_name)
            trade_gate = getattr(module, gate_name)()
        except Exception as e:
            logger.error(f"初始化trade gate失败，error={e}")
            raise

        self._ctx.trade_gate = trade_gate
        account = Account(self._ctx)

        self._ctx.account = account
        portfolio = Portfolio(account)
        self._ctx.portfolio = portfolio

        self._ctx.account.setup(options)

    @property
    def options(self):
        return self._options
