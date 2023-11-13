# -*- coding:utf-8 -*-
import os
import datetime

from importlib import import_module

from jqtrade.scheduler.config import get_config as get_scheduler_config
from jqtrade.account.trade_gate import AbsTradeGate
from jqtrade.scheduler.log import set_log_context, sys_logger

scheduler_config = get_scheduler_config()
scheduler_config.ENABLE_HISTORY_START = True


logger = sys_logger.getChild("test_strategy")


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


class FakeTradeGate(AbsTradeGate):
    def setup(self):
        logger.info("setup")

    def order(self, req):
        logger.info("order. req=%s" % req)

    def cancel_order(self, req):
        logger.info("cancel_order. req=%s" % req)

    def on_confirmed(self, rsp):
        logger.info("on_confirmed, rsp=%s" % rsp)

    def on_deal(self, rsp):
        logger.info("on_deal, rsp=%s" % rsp)

    def on_rejected(self, rsp):
        logger.info("on_rejected, rsp=%s" % rsp)

    def on_canceled(self, rsp):
        logger.info("on_canceled, rsp=%s" % rsp)

    def sync_balance(self):
        logger.info("sync_balance run")
        ret = \
            {
                "cash":
                    {
                            "total_assert": 10000,       # 必需字段，总资产
                            "available_cash": 5000,     # 必需字段，可用资金
                            "locked_cash": 1000,        # 必需字段，冻结资金
                    },
                "positions":
                    [
                        {
                            "code": "000001.XSHE",           # 必需字段，持仓标的
                            "amount": 1000,                  # 必需字段，持仓数量
                            "available_amount": 100,         # 必需字段，可用数量
                            "avg_cost": 11.11,               # 必需字段，持仓成本

                            "side": "long",                  # 可选字段，long | short
                            "last_price": 11.10,             # 可选字段，最新价格
                            "position_value": 111000,        # 可选字段，持仓对应的当前市值
                        },
                    ],
            }
        return ret

    def sync_orders(self):
        logger.info("sync_orders run")
        ret = [
                {
                    "order_id": '1234',                                             # 必填字段，内部委托id
                    "code": "000001.XSHE",                                          # 必填字段，标的代码
                    "price": 11.11,                                                 # 必填字段，委托价格
                    "amount": 1000,                                                 # 必填字段，委托数量
                    "action": "open",                                               # 必填字段，订单行为，开仓open、平仓close
                    "status": "filled",                                              # 必填字段，订单状态
                    "style": "market",                                               # 必填字段，订单类型，市价单market，限价单limit
                    "create_time": datetime.datetime(2023, 11, 6, 10, 30, 33),       # 必填字段，订单创建事件

                    "entrust_time": datetime.datetime(2023, 11, 6, 10, 30, 34),      # 可选字段，订单委托确认时间
                    "confirm_id": '123455',                                          # 可选字段，券商委托ID
                    "filled_amount": datetime.datetime(2023, 11, 6, 10, 30, 34),     # 可选字段，已成数量
                    "canceled_amount": datetime.datetime(2023, 11, 6, 10, 30, 34),   # 可选字段，已撤数量
                    "deal_balance": datetime.datetime(2023, 11, 6, 10, 30, 34),      # 可选字段，已成交金额
                    "avg_cost": datetime.datetime(2023, 11, 6, 10, 30, 34),          # 可选字段，成交均价
                }
            ]
        return ret


def run_strategy(path):
    from jqtrade.scheduler.loop import EventLoop
    from jqtrade.scheduler.bus import EventBus
    from jqtrade.scheduler.event_source import EventSourceScheduler
    from jqtrade.scheduler.loader import Loader
    from jqtrade.scheduler.context import Context
    from jqtrade.scheduler.strategy import Strategy

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

    if scheduler_config.SETUP_ACCOUNT:
        from jqtrade.account.account import Account
        from jqtrade.account.portfolio import Portfolio

        context.trade_gate = FakeTradeGate()

        account = Account(context)
        context.account = account
        account.setup()

        portfolio = Portfolio(account)
        context.portfolio = portfolio

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
