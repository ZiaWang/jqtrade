# -*- coding: utf-8 -*-
import datetime

from ..scheduler.log import sys_logger
from ..scheduler.exceptions import InternalError


logger = sys_logger.getChild("trade_gate")


class AttrDict(object):
    _required_keys = ()

    def __init__(self, **kwargs):
        _lacked_keys = set(self._required_keys) - set(kwargs)
        if _lacked_keys:
            raise InternalError("下单请求缺少 %s 字段数据" % _lacked_keys)

        self._data = dict(**kwargs)

    def __getattr__(self, item):
        if item in self._data:
            return self._data[item]
        return object.__getattribute__(self, item)

    def __getitem__(self, item):
        return self._data[item]

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self._data)


class Request(AttrDict):
    pass


class OrderRequest(Request):
    _required_keys = (
        "order_id",     # 内部委托ID
        "code",         # 标的代码
        "style",        # 委托style，MarketOrderStyle、LimitOrderStyle
        "amount",       # 委托数量，单位：股，正数表示建仓，负数表示平仓
        "side",         # 多做还是做空，OrderSide.long、OrderSide.short
    )


class CancelOrderRequest(Request):
    _required_keys = (
        "order_id",     # 内部委托ID
    )


class Response(AttrDict):
    pass


class AbsTradeGate(object):
    """ 具体对接券商交易接口的类

    Notice:
        1. 函数内部处理行为需要明确，最好不要有默认行为
        2. 接口请求失败/处理订单失败时，抛出异常，上层调用函数catch异常后根据业务场景处理
    """
    def setup(self):
        """ 初始化TradeGate，子类需实现，在策略进程启动初始化account的时候调用 """
        raise NotImplementedError

    def order(self, req):
        """ 委托下单
        Args:
            req: Request对象，封装下单信息

        Raise:
            委托下单失败时抛出异常
        """
        raise NotImplementedError

    def cancel_order(self, req):
        """ 委托撤单
        Args:
            req: Request对象，封装撤单信息

        Raise:
             委托撤单失败时抛出异常
        """
        raise NotImplementedError

    def on_confirmed(self, rsp):
        """ 委托确认回调函数
        Args:
            rsp: Response对象，封装委托确认信息
        """
        raise NotImplementedError

    def on_deal(self, rsp):
        """ 成交回报回调函数

        Args:
            rsp: Response对象，封装成交回报信息
        """
        raise NotImplementedError

    def on_canceled(self, rsp):
        """ 撤单成交回报回调函数

        Args:
            rsp: Response对象，封装撤单回报信息
        """
        raise NotImplementedError

    def on_rejected(self, rsp):
        """ 委托废单回调函数

        Args:
            rsp: Response对象，封装废单信息
        """
        raise NotImplementedError

    def sync_balance(self):
        """ 获取策略资金账户最新资金、持仓信息

        Return:
            {
                "cash":
                        {
                            "total_assert": 0,       # 必需字段，总资产
                            "available_cash": 0,     # 必需字段，可用资金
                            "locked_cash": 0,        # 必需字段，冻结资金
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
                    ]
            }
        """
        raise NotImplementedError

    def sync_orders(self):
        """ 获取策略资金账户最新订单信息

        Return:
            [
                {
                    "order_id": '1234',                                             # 必填字段，内部委托id
                    "code": "000001.XSHE",                                          # 必填字段，标的代码
                    "price": 11.11,                                                 # 必填字段，委托价格
                    "amount": 1000,                                                 # 必填字段，委托数量
                    "action": "open",                                               # 必填字段，订单行为，开仓open、平仓close
                    "status": "filled"                                              # 必填字段，订单状态
                    "style": "market"                                               # 必填字段，订单类型，市价单market，限价单limit
                    "create_time": datetime.datetime(2023, 11, 6, 10, 30, 33)       # 必填字段，订单创建事件

                    "entrust_time": datetime.datetime(2023, 11, 6, 10, 30, 34)      # 可选字段，订单委托确认时间
                    "confirm_id": '123455'                                          # 可选字段，券商委托ID
                    "filled_amount": datetime.datetime(2023, 11, 6, 10, 30, 34)     # 可选字段，已成数量
                    "canceled_amount": datetime.datetime(2023, 11, 6, 10, 30, 34)   # 可选字段，已撤数量
                    "deal_balance": datetime.datetime(2023, 11, 6, 10, 30, 34)      # 可选字段，已成交金额
                    "avg_cost": datetime.datetime(2023, 11, 6, 10, 30, 34)          # 可选字段，成交均价
                }
            ]
        """
        raise NotImplementedError
