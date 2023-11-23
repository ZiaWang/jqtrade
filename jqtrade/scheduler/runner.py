# -*- coding: utf-8 -*-
import os
import sys

from importlib import import_module

from ..common.exceptions import TaskError, ConfigError
from ..common.log import sys_logger, setup_file_logger, setup_logger

from .loader import Loader
from .strategy import Strategy
from .event_source import EventSourceScheduler
from .loop import EventLoop
from .bus import EventBus
from .context import Context
from .utils import get_activate_task_process, parse_task_info
from .config import setup_scheduler_config, get_config as get_scheduler_config


logger = sys_logger.getChild("runner")


def _parse_env(env, sep=";"):
    ret = {}
    envs = env.split(sep)
    for _env in envs:
        _env = _env.strip()
        _k, _v = _env.split("=")
        _k = _k.strip()
        _v = _v.strip()
        ret[_k] = _v
    return ret


def _exist_repeated_task(task_name):
    current_pid = os.getpid()
    parent_pid = os.getppid()

    active_tasks = get_activate_task_process()
    for _task in active_tasks:
        if _task.pid in (current_pid, parent_pid):
            continue
        _task_info = parse_task_info(_task.cmdline())
        if task_name == _task_info["name"]:
            return True


class TaskRunner(object):
    """ 启动策略进程的入口类 """

    def __init__(self, code_file, out_file, task_name, env, debug=False, config=None):
        if not os.path.exists(code_file):
            raise FileNotFoundError("code file not found, path=%s" % code_file)
        self._code_file = code_file

        if _exist_repeated_task(task_name):
            raise TaskError("task(%s) already exists" % task_name)

        self._task_name = task_name

        self._out_file = out_file
        log_level = "DEBUG" if debug else "INFO"
        if out_file:
            setup_file_logger(out_file, log_level)
        else:
            setup_logger(log_level)

        self._env = _parse_env(env) if env else {}
        os.environ.update(self._env)
        if "PYTHONPATH" in self._env:
            sys.path.extend(self._env["PYTHONPATH"].split(":"))

        self._debug = debug

        if config:
            path = os.path.expanduser(config)
            if not os.path.exists(path):
                raise FileNotFoundError("找不到自定义配置文件: %s" % path)
        self._config = config

    def run(self):
        logger.info("start strategy runner. code_file=%s, out_file=%s, task_name=%s, env=%s, debug=%s" % (
            self._code_file, self._out_file, self._task_name, self._env, self._debug
        ))

        if self._config:
            setup_scheduler_config(self._config)

        event_loop = EventLoop()
        context = Context(task_name=self._task_name,
                          event_bus=EventBus(),
                          loop=event_loop,
                          scheduler=EventSourceScheduler(),
                          loader=Loader(self._code_file),
                          debug=self._debug)

        scheduler_config = get_scheduler_config()
        if scheduler_config.SETUP_ACCOUNT:
            from ..account.account import Account
            from ..account.portfolio import Portfolio
            from ..account.config import setup_account_config, get_config as get_account_config
            if self._config:
                setup_account_config(self._config)
            account_config = get_account_config()
            if not account_config.TRADE_GATE:
                raise ConfigError("未配置 trade gate，")

            module_name, gate_name = account_config.TRADE_GATE.rsplit(".", 1)
            module = import_module(module_name)
            trade_gate = getattr(module, gate_name)()
            context.trade_gate = trade_gate
            account = Account(context)
            context.account = account
            portfolio = Portfolio(account)
            context.portfolio = portfolio

        strategy = Strategy(context)
        strategy.setup()

        event_loop.run()
