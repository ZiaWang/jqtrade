# -*- coding: utf-8 -*-
import os
import sys

from ..common.exceptions import TaskError
from ..common.log import sys_logger, setup_file_logger, setup_logger

from .loader import Loader
from .strategy import Strategy
from .event_source import EventSourceScheduler
from .loop import EventLoop
from .bus import EventBus
from .context import Context
from .utils import get_activate_task_process, parse_task_info, parse_env
from .config import setup_scheduler_config, get_config as get_scheduler_config


logger = sys_logger.getChild("runner")


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
    """
    Usage:
        1. 解析启动参数
        2. 检查和初始化启动环境
        3. 启动策略进程
    """

    def __init__(self, code_file, out_file, task_name, env, debug=False, config=None):
        if not os.path.exists(code_file):
            raise FileNotFoundError(f"未找到策略代码文件，path={code_file}")
        self._code_file = code_file

        if _exist_repeated_task(task_name):
            raise TaskError(f"检测到机器上已经运行了任务：{task_name}，不能重复运行名称相同的任务，"
                            f"需要停止该重复任务或修改当前任务名称避免重复")

        self._task_name = task_name

        self._debug = debug
        log_level = "DEBUG" if debug else "INFO"
        self._out_file = out_file
        if out_file:
            setup_file_logger(out_file, log_level)
        else:
            setup_logger(log_level)

        self._env = parse_env(env) if env else {}
        os.environ.update(self._env)
        if "PYTHONPATH" in self._env:
            for _py_path in reversed(self._env["PYTHONPATH"].split(":")):
                sys.path.insert(0, _py_path)

        if config:
            path = os.path.abspath(os.path.expanduser(config))
            if not os.path.exists(path):
                raise FileNotFoundError(f"找不到自定义配置文件: {path}")
        self._config = config

    def run(self):
        logger.info(f"开始启动策略进程。策略代码路径：{self._code_file}, 日志文件：{self._out_file}, "
                    f"任务名称：{self._task_name}，环境变量：{self._env}, debug模式：{self._debug}")

        if self._config:
            logger.info(f"scheduler模块加载用户自定义配置：{self._config}")
            setup_scheduler_config(self._config)

        event_loop = EventLoop()
        context = Context(task_name=self._task_name,
                          event_bus=EventBus(),
                          loop=event_loop,
                          scheduler=EventSourceScheduler(),
                          loader=Loader(self._code_file),
                          debug=self._debug,
                          config=self._config,
                          out=self._out_file)

        strategy = Strategy(context)
        strategy.setup()

        event_loop.run()
