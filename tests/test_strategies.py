# -*- coding:utf-8 -*-
import os
import datetime

from quant_engine.scheduler.config import get_config
from quant_engine.scheduler.log import set_log_context

scheduler_config = get_config()
scheduler_config.ENABLE_HISTORY_START = True


def get_setting(path, setting):
    import re
    c = open(path).read()
    has_setting = re.search(r'^' + setting, c, flags=re.M) is not None
    g = re.search(r'^%s\s*=(.*?^[\}\]])' % setting, c, flags=re.M | re.S)
    assert bool(g) == has_setting
    if g:
        return eval(g.group(1))
    else:
        return {}


def parse_dt(dt):
    if isinstance(dt, datetime.date):
        return datetime.datetime.combine(dt, datetime.time(0, 0))
    elif isinstance(dt, datetime.datetime):
        return dt
    elif isinstance(dt, str):
        if " " in dt:
            dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.datetime.strptime(dt, "%Y-%m-%d")
        return dt


def run_strategy(path):
    from quant_engine.scheduler.loop import EventLoop
    from quant_engine.scheduler.bus import EventBus
    from quant_engine.scheduler.event_source import EventSourceScheduler
    from quant_engine.scheduler.loader import Loader
    from quant_engine.scheduler.context import Context
    from quant_engine.scheduler.strategy import Strategy

    options = get_setting(path, "__options__")

    start = options.get("start", None)
    if start:
        start = parse_dt(start)

    end = options.get("end", None)
    if end:
        end = parse_dt(end)

    event_loop = EventLoop()
    context = Context(event_bus=EventBus(),
                      loop=event_loop,
                      scheduler=EventSourceScheduler(),
                      loader=Loader(path),
                      debug=options.get("debug", False),
                      start=start,
                      end=end)

    set_log_context(context)

    strategy = Strategy(context)
    strategy.setup()

    event_loop.run()

    if hasattr(strategy.user_module, "process_exit"):
        getattr(strategy.user_module, "process_exit")(strategy.user_module.context)


def create_tests():
    this_dir = os.path.abspath(os.path.dirname(__file__))
    tests_dir = os.path.join(this_dir, "strategies")

    g = globals()
    for _strategy in os.listdir(tests_dir):
        if not _strategy.endswith(".py"):
            continue

        _strategy_path = os.path.join(tests_dir, _strategy)
        _func = create_test_func(_strategy_path)
        g[_func.__name__] = _func


def create_test_func(path):
    strategy = os.path.basename(path)

    func_name = "test_" + strategy.replace(".py", "")

    def func():
        run_strategy(path)

    func.__name__ = func_name
    func.__doc__ = func_name

    return func


create_tests()
