# -*- coding: utf-8 -*-
import os


class AccountConfig(object):
    _instance = None

    def __init__(self):
        # 是否从券商接口同步资金、持仓
        self.SYNC_BALANCE = True

        # 是否从券商接口同步订单
        self.SYNC_ORDER = True

        # 同步资金、持仓、订单时间间隔，单位：秒
        self.SYNC_INTERNAL = 5

        # 同步资金、持仓、订单时间区间，不设置时默认启动期间一直同步
        self.SYNC_PERIOD = [
            # (datetime.time(9, 30), datetime.time(11, 30)),
            # (datetime.time(13, 0), datetime.time(15, 0)),
        ]

        # 默认使用的trade_gate，配置成空字符串或None时，不加载account模块
        self.TRADE_GATE = "jqtrade.account.trade_gate.AnXinDMATradeGate"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def _load_config(path):
    configs = {}
    exec(open(path).read(), {}, configs)

    account_configs = {}
    for _name in configs:
        if _name.startswith("ACCOUNT_"):
            account_configs[_name.lstrip("ACCOUNT_")] = configs[_name]
    return account_configs


def get_config():
    return AccountConfig.get_instance()


def setup_account_config(path):
    path = os.path.abspath(os.path.expanduser(path))
    config = AccountConfig.get_instance()
    custom_config = _load_config(path)
    config.__dict__.update(custom_config)
