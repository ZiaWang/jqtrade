# -*- coding: utf-8 -*-
import os
import datetime


class SchedulerConfig(object):
    _instance = None

    def __init__(self):
        # event_source默认生成最近365天的事件
        self.EVENT_DAYS_COUNT = 365

        # 支持从历史时间开始生成事件，用于跑测试用例，实盘中请勿开启
        self.ENABLE_HISTORY_START = False

        # 交易时间段设置
        self.MARKET_OPEN_TIME = datetime.time(9, 30)
        self.MARKET_CLOSE_TIME = datetime.time(15, 0)
        self.MARKET_PERIOD = [
            (datetime.time(9, 30), datetime.time(11, 30)),
            (datetime.time(13, 0), datetime.time(15, 0)),
        ]

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def _load_config(path):
    configs = {}
    exec(open(path).read(), {}, configs)

    scheduler_configs = {}
    for _name in configs:
        if _name.startswith("SCHEDULER_"):
            scheduler_configs[_name.lstrip("SCHEDULER_")] = configs[_name]
    return scheduler_configs


def get_config():
    return SchedulerConfig.get_instance()


def setup_scheduler_config(path):
    path = os.path.abspath(os.path.expanduser(path))
    config = SchedulerConfig.get_instance()
    custom_config = _load_config(path)
    config.__dict__.update(custom_config)


if __name__ == '__main__':
    cfg = get_config()
    print(cfg.MARKET_PERIOD)
    setup_scheduler_config("~/quant_engine_etc.py")
    print(cfg.MARKET_PERIOD)
