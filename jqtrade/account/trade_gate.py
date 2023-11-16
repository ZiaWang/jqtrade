# -*- coding: utf-8 -*-
import os
import time
import json
import datetime
import portalocker

from collections import namedtuple

import pandas as pd
from pandas.errors import ParserError

from ..scheduler.log import sys_logger
from ..scheduler.context import Context
from ..scheduler.exceptions import InternalError, InvalidParam, TimeOut
from ..scheduler.config import get_config as get_scheduler_config

from .order import OrderSide, MarketOrderStyle, Order, OrderAction, LimitOrderStyle, OrderStatus
from .utils import simple_retry


logger = sys_logger.getChild("trade_gate")


scheduler_config = get_scheduler_config()


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

    def __init__(self):
        # 存放策略交易接口相关必要信息
        self._options = None

    def setup(self):
        """ 初始化TradeGate，子类需实现，在策略进程启动初始化account的时候调用 """
        raise NotImplementedError

    def order(self, user_order):
        """ 委托下单
        Args:
            user_order: Order对象

        Raise:
            委托下单失败时抛出异常
        """
        raise NotImplementedError

    def cancel_order(self, order_id):
        """ 委托撤单
        Args:
            order_id: 被撤订单的内部委托id

        Raise:
             委托撤单失败时抛出异常
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

    def set_options(self, **kwargs):
        self._options = kwargs


class AnXinDMATradeGate(AbsTradeGate):
    ACCOUNT_TYPES = {
        "stock": "UMO",     # 普通股票账户
    }

    TRADE_SIDES = {
        "B": 1,
        "S": 2
    }

    ALGO_ID = "DMA"

    WAIT_LOCK_INTERNAL = 0.05
    WAIT_LOCK_TIME_OUT = 5

    ORDER_LINE_COLS = ("updTime", "orderDate", "orderTime", "acctType",
                       "acct", "symbol", "tradeSide", "status", "orderQty",
                       "orderPrice", "orderType", "filledQty", "avgPrice",
                       "filledAmt", "cancelQty", "orderNo", "corrId",
                       "custBatchNo", "text", "cliOrderId")
    ORDER_LINE_CLS = namedtuple("OrderLine", ORDER_LINE_COLS)

    ORDER_INFO_COLS = ("code", "price", "amount", "action",
                       "order_id", "status", "style", "create_time", "entrust_time",
                       "side", "confirm_id", "filled_amount", "canceled_amount",
                       "deal_balance", "avg_cost", "err_msg")
    ORDER_INFO_CLS = namedtuple("OrderInfo", ORDER_INFO_COLS)

    STATUS_MAP = {
            "0": OrderStatus.open,
            "1": OrderStatus.filling,
            "2": OrderStatus.filled,
            "3": OrderStatus.partly_canceled,
            "4": OrderStatus.canceled,
            "5": OrderStatus.rejected,
            "7": OrderStatus.new,
            "8": OrderStatus.canceling,
    }

    DATA_DIR = os.path.join(scheduler_config.ROOT_DIR, "data")

    def __init__(self):
        super(AnXinDMATradeGate, self).__init__()

        self._date = datetime.date.today()
        self._order_csv = self._date.strftime("algoOrder_%%%m%d.csv")
        self._cancel_csv = self._date.strftime("algoOrderStop_%%%m%d.csv")
        self._order_result_csv = self._date.strftime("execResult_%Y%m%d.csv")
        self._order_update_csv = self._date.strftime("orderUpdate_%Y%m%d.csv")
        self._trade_update_csv = self._date.strftime("tradeUpdate_%Y%m%d.csv")
        self._assert_info_csv = self._date.strftime("assertInfo_%Y%m%d.csv")
        self._position_info_csv = self._date.strftime("positionInfo_%Y%m%d.csv")

        # 持久化存储策略与订单映射关系，用于重启加载恢复订单
        ctx = Context.get_instance()
        self._data_dir = os.path.abspath(os.path.expanduser("~/jqtrade"))
        self._data_file = os.path.join(self.DATA_DIR, "%s_%s.json" % (ctx.task_name, self._date.strftime("%Y%m%d")))

        # 缓存当日订单. key: order_id, value: dict
        self._orders = {}
        self._order_update_offset = 0

        self._options = None

    def order(self, user_order):
        acct_no = self._options.get("account_no")
        if not acct_no:
            raise InvalidParam("未设置account_no信息，请使用set_account设置资金账号")

        account_type = self._options.get("account_type", "stock")
        if account_type not in self.ACCOUNT_TYPES:
            raise InvalidParam("当前版本仅支持%s类型账户交易" % list(self.ACCOUNT_TYPES.keys()))
        acct_type = self.ACCOUNT_TYPES[account_type]

        if user_order.side != OrderSide.long:
            raise InvalidParam("当前版本仅支持做多")

        now = datetime.datetime.now()
        order_info = [now.strftime("%H%M%S.%f"), user_order.order_id,
                      acct_type, acct_no,
                      self._encode_security(user_order.code)]

        if user_order.amount > 0:
            order_info.append(self.TRADE_SIDES["B"])
        else:
            order_info.append(self.TRADE_SIDES["S"])

        order_info.append(abs(user_order.amount))
        order_info.append(self.ALGO_ID)

        if isinstance(user_order.style, MarketOrderStyle):
            if user_order.amount > 0:
                order_info.extend(["P6", 0, 0, 0])     # 涨停价
            else:
                order_info.extend(["P7", 0, 0, 0])     # 跌停价
        else:
            limit_price = user_order.style.price
            order_info.extend(["AT", 0, limit_price, limit_price])

        order_info = [str(i) for i in order_info]
        order_line = ",".join(order_info) + os.linesep
        self._write(self._order_csv, order_line)

        self._orders[user_order.order_id] = user_order.json()

    def cancel_order(self, order_id):
        now = datetime.datetime.now()
        order_info = [now.strftime("%H%M%S.%f"), str(order_id)]
        order_line = ",".join(order_info) + os.linesep
        self._write(self._cancel_csv, order_line)

    def _write(self, file, line, mode="a"):
        start = time.time()
        while True:
            with open(file, mode) as fp:
                try:
                    portalocker.lock(fp, portalocker.LOCK_EX | portalocker.LOCK_NB)  # no block
                    fp.write(line)
                    break
                except BlockingIOError:
                    if time.time() - start >= self.WAIT_LOCK_TIME_OUT:
                        raise TimeOut("waiting file lock time out")
                    time.sleep(self.WAIT_LOCK_INTERNAL)
                finally:
                    portalocker.unlock(fp)

    def sync_balance(self):
        data = {}

        if not os.path.exists(self._assert_info_csv):
            raise FileNotFoundError("找不到资产信息文件单：%s，"
                                    "请检查one quant是否启动或文件单是否开启定时导出模式" % self._assert_info_csv)

        asset_info = self._read_csv(self._assert_info_csv).loc[0]
        data["cash"] = {
            "total_asset": float(asset_info["totalAsset"]),
            "available_cash": float(asset_info["enabledBalance"]),
            "locked_cash": float(asset_info["currentBalance"]) - float(asset_info["enabledBalance"]),
        }

        if not os.path.exists(self._position_info_csv):
            raise FileNotFoundError("找不到持仓信息文件单：%s，"
                                    "请检查one quant是否启动或文件单是否开启定时导出模式" % self._position_info_csv)
        data["positions"] = []
        position_info = self._read_csv(self._position_info_csv)
        for _pos in position_info.itertuples():

            # 最后一行
            if pd.isna(_pos.symbol):
                break

            data["positions"].append({
                "code": self._decode_security(str(_pos.symbol)),
                "amount": int(_pos.currentQty),
                "available_amount": int(_pos.enabledQty),
                "avg_cost": float(_pos.costPrice),

                "side": OrderSide.long,
                "last_price": float(_pos.lastPrice),
                "position_value": float(_pos.mktValue),
            })

        return data

    @staticmethod
    @simple_retry(on_exception=lambda e: isinstance(e, (OSError, ParserError)))
    def _read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        if not df.loc[len(df)-1].isna().all():
            raise OSError("file not complete")
        return df

    @staticmethod
    def _decode_security(code):
        if code.endswith("SZ"):
            return code.replace("SZ", "XSHE")
        elif code.endswith("SH"):
            return code.replace("SH", "XSHG")
        else:
            raise ValueError("invalid code: %s" % code)

    @staticmethod
    def _encode_security(code):
        if code.endswith("XSHE"):
            return code.replace("XSHE", "SZ")
        elif code.endswith("XSHG"):
            return code.replace("XSHG", "SH")
        else:
            raise ValueError("invalid code: %s" % code)

    def sync_orders(self, notify=False):
        pre_offset = self._order_update_offset
        with open(self._order_update_csv, "r", encoding="gbk") as rf:
            rf.seek(pre_offset)
            while True:
                try:
                    _line = rf.readline()
                    if not _line:
                        break

                    if _line.startswith(self.ORDER_LINE_COLS[0]):
                        self._order_update_offset = rf.tell()
                        continue

                    _items = [_s.strip() for _s in _line.split(",")]
                    if len(_items) != len(self.ORDER_LINE_COLS):
                        raise ParserError("invalid line, offset=%s, line=%s" % (rf.tell(), _line))

                    order_line = self.ORDER_LINE_CLS(*_items)

                    if order_line.custBatchNo not in self._orders:
                        continue

                    self._update_order(self._orders[order_line.custBatchNo], order_line)

                    # 记录下当前成功解析了的订单的位置
                    self._order_update_offset = rf.tell()
                except EOFError:
                    break

        self._save_orders()

        data = []
        for _order in self._orders.values():
            data.append(_order.copy())
        return data

    def _update_order(self, order, order_line):
        order["status"] = self._parse_status(order_line.status)
        order["entrust_time"] = datetime.datetime.strptime(order_line.orderDate + order_line.orderTime,
                                                           "%Y%m%d%H%M%S")
        order["confirm_id"] = order_line.orderNo
        order["filled_amount"] = order_line.filledQty
        order["deal_balance"] = order_line.filledAmt
        order["canceled_amount"] = order_line.cancelQty
        order["avg_cost"] = order_line.avgPrice
        order["err_msg"] = order_line.text

    def _save_orders(self):

        with open(self._data_file, "w") as wf:
            json.dump(self._orders, wf)

    def _load_orders(self):
        if not os.path.exists(self._data_file):
            return

        with open(self._data_file, "r") as rf:
            self._orders = json.load(rf)

    def _parse_status(self, status):
        if status not in self.STATUS_MAP:
            raise ParserError("unknown status: %s" % status)
        return self.STATUS_MAP[status]

    def setup(self):
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)

        order_dir = self._options.get("order_dir")
        if not order_dir:
            raise InvalidParam("使用安信one quant时，请使用set_options设置order_dir选项，指定文件单目录路径")

        if not os.path.exists(order_dir):
            raise FileNotFoundError("文件单目录不存在（%s），请检查是否已开启安信one quant并打开文件单导出选项" % order_dir)

        date_s = self._date.strftime("%Y%m%d")
        self._order_csv = os.path.join(order_dir, "algoOrder_%s.csv" % date_s)
        self._cancel_csv = os.path.join(order_dir, "algoOrderStop_%s.csv" % date_s)
        self._order_result_csv = os.path.join(order_dir, "execResult_%s.csv" % date_s)
        self._order_update_csv = os.path.join(order_dir, "orderUpdate_%s.csv" % date_s)
        self._trade_update_csv = os.path.join(order_dir, "tradeUpdate_%s.csv" % date_s)
        self._assert_info_csv = os.path.join(order_dir, "assetInfo_%s.csv" % date_s)
        self._position_info_csv = os.path.join(order_dir, "positionInfo_%s.csv" % date_s)

        self._load_orders()
