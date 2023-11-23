# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import shutil
import datetime
import portalocker

from collections import namedtuple

import pandas as pd
from pandas.errors import ParserError

from ..common.exceptions import InvalidParam, TimeOut
from ..common.log import sys_logger
from ..common.utils import simple_retry
from ..scheduler.context import Context
from ..scheduler.config import get_config as get_scheduler_config

from .order import OrderSide, MarketOrderStyle, OrderStatus, OrderAction
from .config import get_config as get_account_config


logger = sys_logger.getChild("trade_gate")


scheduler_config = get_scheduler_config()
account_config = get_account_config()


class AbsTradeGate(object):
    """ 具体对接券商交易接口的类

    Notice:
        1. 函数内部处理行为需要明确，最好不要有默认行为
        2. 接口请求失败/处理订单失败时，抛出异常，上层调用函数catch异常后根据业务场景处理
    """

    def __init__(self):
        # 存放策略交易接口相关必要信息
        self._options = None

    def setup(self, options):
        """ 初始化TradeGate，子类需实现，在策略进程启动初始化account的时候调用 """
        raise NotImplementedError

    def order(self, sys_order):
        """ 委托下单
        Args:
            sys_order: Order对象

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


class AnXinDMAError(Exception):
    pass


class AnXinDMATradeGate(AbsTradeGate):
    """ 安信one quant专用交易接口

    支持的options:
        "account_no": 资金账号
        "account_type": 策略账户类型
            支持：
                STOCK：目前仅支持股票类型
        "counter_type": 柜台类型
            支持：
                UM0 普通股票账户【默认此类型】
                UF0 金证极速股票账户
                AT0 华锐极速股票账户
                UMC 普通信用账户【信用账户暂时不支持】
                UFC 金证极速信用账户【信用账户暂时不支持】
        "algo_type": 算法交易类型
            支持：
                DMA：目前仅支持DMA
        "wait_lock_internal": 写文件单时，文件锁轮训间隔，默认0.05秒
        "wait_lock_time_out": 写文件单时，文件锁轮训超时，默认5秒
        "file_encoding": 文件单编码类型，默认使用sys.getfilesystemencoding()返回值
        "order_dir": 文件单所在目录路径，默认是 C:\Ax\国投OneQuant\csvTemplate\DMA算法\
        "sync_retry_kwargs": 读取解析文件单失败重试次数。
            格式：
                {
                    "max_attempts": 3,          # 默认最大重试3次
                    "attempt_internal": 0.15       # 默认每次重试间隔0.15秒
                }
        "ignore_error_line": 解析订单状态文件时，是否忽略掉解析失败的订单信息
    """
    DEFAULT_ACCOUNT_TYPE = "STOCK"
    DEFAULT_COUNTER_TYPE = "UM0"
    DEFAULT_ALGO_TYPE = "DMA"
    DEFAULT_ORDER_DIR = r"C:\Ax\国投OneQuant\csvTemplate\DMA算法"
    DEFAULT_SYNC_RETRY_KWARGS = {
        "max_attempts": 3,
        "attempt_internal": 0.15
    }
    DEFAULT_IGNORE_ERROR_LINE = True

    TRADE_SIDES = {
        "B": 1,
        "S": 2
    }

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

    ORDER_RESULT_COLS = ("updTime", "resultType", "custBatchNo", "status", "errorCode", "errorMsg")
    ORDER_RESULT_CLS = namedtuple("OrderResult", ORDER_RESULT_COLS)

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

    RESULT_REJECT_STATUS = "1"
    RESULT_TYPE_ORDER = "1"
    RESULT_TYPE_CANCEL = "2"

    ORDER_CSV_HEADER = "updTime,custBatchNo,acctType,acct,symbol,tradeSide," \
                       "targetQty,algoId,priceType,ticks,highLimitPrice,lowLimitPrice"

    CANCEL_CSV_HEADER = "updTime,custBatchNo"

    def __init__(self):
        super(AnXinDMATradeGate, self).__init__()

        # 持久化存储策略与订单映射关系，用于重启加载恢复订单
        self._data_dir = None
        self._data_file = None

        # 文件单目录
        self._order_dir = None

        # 缓存当日订单. key: order_id, value: dict
        self._orders = {}
        self._order_update_offset = 0
        self._order_result_offset = 0

        self._has_synced = False

        self._file_coding = None

        self._wait_lock_internal = None
        self._wait_lock_time_out = None

        self._ignore_error_line = None

        self._counter_type = None
        self._algo_type = None

    def order(self, sys_order):
        acct_no = self._options.get("account_no")
        if not acct_no:
            raise InvalidParam("未设置account_no信息，请使用set_account设置资金账号")

        account_type = self._options.get("account_type", self.DEFAULT_ACCOUNT_TYPE)
        if account_type != self.DEFAULT_ACCOUNT_TYPE:
            raise InvalidParam(f"当前版本仅支持{self.DEFAULT_ACCOUNT_TYPE}类型账户交易")

        if sys_order.side != OrderSide.long:
            raise InvalidParam("当前版本仅支持做多")

        now = datetime.datetime.now()
        order_info = [now.strftime("%H%M%S.%f"), sys_order.order_id,
                      self._counter_type, acct_no,
                      self._encode_security(sys_order.code)]

        if sys_order.action == OrderAction.open:
            order_info.append(self.TRADE_SIDES["B"])
        else:
            order_info.append(self.TRADE_SIDES["S"])

        order_info.extend([abs(sys_order.amount), self._algo_type])

        if isinstance(sys_order.style, MarketOrderStyle):
            if sys_order.action == OrderAction.open:
                order_info.extend(["P6", 0, 0, 0])     # 涨停价
            else:
                order_info.extend(["P7", 0, 0, 0])     # 跌停价
        else:
            limit_price = sys_order.style.price
            order_info.extend(["AT", 0, limit_price, limit_price])

        order_info = [str(i) for i in order_info]
        order_line = ",".join(order_info) + os.linesep
        self._write(self._order_csv, order_line, header=self.ORDER_CSV_HEADER)

        logger.info(f"订单已提交到文件单，订单id：{sys_order.order_id}")

        self._orders[sys_order.order_id] = sys_order.json()
        self._save_orders()

    def cancel_order(self, order_id):
        now = datetime.datetime.now()
        order_info = [now.strftime("%H%M%S.%f"), str(order_id)]
        order_line = ",".join(order_info) + os.linesep
        self._write(self._cancel_csv, order_line, header=self.CANCEL_CSV_HEADER)
        logger.info(f"撤单已提交到文件单，订单id：{order_id}")

    def _write(self, file, line, mode="a", header=None):
        start = time.time()
        while True:
            with open(file, mode, encoding=self._file_coding) as fp:
                try:
                    portalocker.lock(fp, portalocker.LOCK_EX | portalocker.LOCK_NB)  # no block
                    if fp.tell() == 0 and header:
                        line = header + os.linesep + line
                    fp.write(line)
                    break
                except (BlockingIOError, portalocker.exceptions.AlreadyLocked):
                    if time.time() - start >= self._wait_lock_time_out:
                        raise TimeOut("waiting file lock time out")
                    time.sleep(self._wait_lock_internal)
                finally:
                    portalocker.unlock(fp)

    def sync_balance(self):
        data = {}

        self.check_file_exists(self._assert_info_csv)

        acct_no = self._options.get("account_no")
        if not acct_no:
            raise InvalidParam("未设置account_no信息，请使用set_account设置资金账号")

        acct_no = str(acct_no)
        asset_infos = self._read_csv(self._assert_info_csv, dtype={"acct": str, "exchange": str})
        if len(asset_infos) == 0:
            raise AnXinDMAError("文件单中未查询到资产数据")
        for _asset_info in asset_infos.itertuples():
            if _asset_info.acct != acct_no:
                continue

            if not pd.isna(_asset_info.exchange):
                continue

            data["cash"] = {
                "total_asset": round(float(_asset_info.totalAsset), 4),
                "available_cash": round(float(_asset_info.enabledBalance), 4),
                "locked_cash": round(float(_asset_info.currentBalance) - float(_asset_info.enabledBalance), 4),
            }

        self.check_file_exists(self._position_info_csv)

        data["positions"] = []
        position_info = self._read_csv(self._position_info_csv, dtype={"acct": str, "symbol": str})
        for _pos in position_info.itertuples():
            if _pos.acct != acct_no:
                continue

            # 最后一行
            if pd.isna(_pos.symbol):
                break

            # 过滤掉当前持仓量为0的持仓
            if int(_pos.currentQty) == 0:
                continue

            data["positions"].append({
                "code": self._decode_security(str(_pos.symbol)),
                "amount": int(_pos.currentQty),
                "available_amount": int(_pos.enabledQty),
                "avg_cost": round(float(_pos.costPrice), 3),

                "side": OrderSide.long,
                "last_price": round(float(_pos.lastPrice), 3),
                "position_value": round(float(_pos.mktValue), 4),
            })

        return data

    @staticmethod
    def check_file_exists(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到文件单：{path}，请检查one quant是否启动或文件单是否开启定时导出模式")

    @classmethod
    def _read_csv(cls, *args, **kwargs):
        path = args[1]
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        df = pd.read_csv(*args[1:], **kwargs)
        if not df.loc[len(df)-1].isna().all():
            raise OSError(f"检测到文件不完整：{path}")
        return df

    @staticmethod
    def _decode_security(code):
        if code.endswith("SZ"):
            return code.replace("SZ", "XSHE")
        elif code.endswith("SH"):
            return code.replace("SH", "XSHG")
        else:
            raise ValueError(f"invalid code: {code}")

    @staticmethod
    def _encode_security(code):
        if code.endswith("XSHE"):
            return code.replace("XSHE", "SZ")
        elif code.endswith("XSHG"):
            return code.replace("XSHG", "SH")
        else:
            raise ValueError(f"invalid code: {code}")

    def sync_orders(self):
        pre_order_update_offset = self._order_update_offset
        pre_order_result_offset = self._order_result_offset

        self.check_file_exists(self._order_update_csv)
        self.check_file_exists(self._order_result_csv)

        with open(self._order_result_csv, "r") as rf:
            rf.seek(pre_order_result_offset)
            while True:
                try:
                    _line = rf.readline().strip()
                    if not _line:
                        break

                    if _line.startswith(self.ORDER_RESULT_COLS[0]):
                        self._order_result_offset = rf.tell()
                        continue

                    _items = [_s.strip() for _s in _line.split(",")]
                    if len(_items) < len(self.ORDER_RESULT_COLS):
                        break

                    _order_result_line = self.ORDER_RESULT_CLS(*_items)
                    if _order_result_line.resultType == self.RESULT_TYPE_CANCEL \
                            and _order_result_line.status == self.RESULT_REJECT_STATUS:
                        if self._has_synced:
                            logger.info(f"撤单失败，被撤单id：{_order_result_line.custBatchNo}，"
                                        f"失败原因：{_order_result_line.errorMsg}")
                        self._order_result_offset = rf.tell()
                        continue

                    if _order_result_line.resultType == self.RESULT_TYPE_ORDER \
                            and _order_result_line.status == self.RESULT_REJECT_STATUS:
                        _order = self._orders.get(_order_result_line.custBatchNo)
                        if _order:
                            _order["status"] = OrderStatus.rejected.value
                            _order["err_msg"] = _order_result_line.errorMsg
                    self._order_result_offset = rf.tell()
                except EOFError:
                    pass
                except Exception as e:
                    logger.exception(f"{self._order_result_csv}中有一笔订单状态信息同步失败，error={e}")
                    if self._ignore_error_line:
                        self._order_result_offset = rf.tell()
                    else:
                        raise

        with open(self._order_update_csv, "r", encoding=self._file_coding) as rf:
            rf.seek(pre_order_update_offset)
            while True:
                try:
                    _line = rf.readline().strip()
                    if not _line:
                        break

                    if _line.startswith(self.ORDER_LINE_COLS[0]):
                        self._order_update_offset = rf.tell()
                        continue

                    _items = [_s.strip() for _s in _line.split(",")]
                    if len(_items) < len(self.ORDER_LINE_COLS):
                        break

                    order_line = self.ORDER_LINE_CLS(*_items)

                    if order_line.custBatchNo not in self._orders:
                        continue

                    self._update_order(self._orders[order_line.custBatchNo], order_line)

                    # 记录下当前成功解析了的订单的位置
                    self._order_update_offset = rf.tell()
                except EOFError:
                    break
                except Exception as e:
                    logger.exception(f"{self._order_update_csv}中有一笔订单状态信息同步失败, error={e}")
                    if self._ignore_error_line:
                        self._order_update_offset = rf.tell()
                    else:
                        raise

        self._has_synced = True
        self._save_orders()

        data = []
        for _order in self._orders.values():
            data.append(_order.copy())
        return data

    def _update_order(self, order, order_line):
        order["status"] = self._parse_status(order_line.status).value
        order["entrust_time"] = datetime.datetime.strptime(order_line.orderDate + order_line.orderTime,
                                                           "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S.%f")
        order["confirm_id"] = order_line.orderNo
        order["filled_amount"] = int(order_line.filledQty)
        order["deal_balance"] = round(float(order_line.filledAmt), 4)
        order["canceled_amount"] = int(order_line.cancelQty)
        order["avg_cost"] = round(float(order_line.avgPrice), 3)
        order["err_msg"] = order_line.text

    def _save_orders(self):
        tmp_file = self._data_file + ".tmp"
        with open(tmp_file, "w") as wf:
            json.dump(self._orders, wf)
        shutil.move(tmp_file, self._data_file)

    def _load_orders(self):
        logger.info(f"从本地缓存文件恢复策略当日订单信息，data_file：{self._data_file}")
        if not os.path.exists(self._data_file):
            logger.info(f"本地无策略当日订单缓存文件，忽略加载历史订单信息，data_file：{self._data_file}")
            return

        try:
            with open(self._data_file, "r") as rf:
                orders = json.load(rf)
                for _order_id, _order_info in orders.items():
                    logger.info(f"加载订单，id：{_order_id}，order_info：{_order_info}")
                self._orders = orders
        except Exception as e:
            logger.exception(f"从本地缓存文件恢复策略当日订单信息失败，error={e}")

    def _parse_status(self, status):
        if status not in self.STATUS_MAP:
            raise ParserError(f"无效订单状态：{status}")
        return self.STATUS_MAP[status]

    def setup(self, options):
        logger.info("setup trade gate")
        self._options = options

        self._order_dir = self._options.get("order_dir", self.DEFAULT_ORDER_DIR)
        logger.info(f"安信one quant文件单路径: {self._order_dir}")
        if not os.path.exists(self._order_dir):
            raise FileNotFoundError(f"文件单目录不存在（{self._order_dir}），请检查是否已开启安信one quant并打开文件单导出选项")

        self._counter_type = self._options.get("counter_type", self.DEFAULT_COUNTER_TYPE)
        if self._counter_type != self.DEFAULT_COUNTER_TYPE:
            logger.warn(f"检测到当前使用的柜台账户类型是{self._counter_type}, 请与您的客户经理确认是否开通了此柜台账户类型，否则将影响交易")

        self._algo_type = self._options.get("algo_type", self.DEFAULT_ALGO_TYPE)
        if self._algo_type != self.DEFAULT_ALGO_TYPE:
            logger.warn(f"检测到当前使用的算法交易类型是{self._algo_type}, 请与您的客户经理确认是否开通了此算法交易类型，否则将影响交易")

        ctx = Context.get_instance()
        runtime_dir = options.get("runtime_dir", scheduler_config.RUNTIME_DIR)

        self._data_dir = os.path.join(runtime_dir, "data")
        logger.info(f"程序缓存数据路径: {self._data_dir}")
        if not os.path.exists(self._data_dir):
            os.makedirs(self._data_dir)

        self._data_file = os.path.join(self._data_dir, f"{ctx.task_name}_{self._date.strftime('%Y%m%d')}.json")

        self._file_coding = self._options.get("file_encoding", sys.getfilesystemencoding())
        self._ignore_error_line = self._options.get("ignore_error_line", self.DEFAULT_IGNORE_ERROR_LINE)

        _sync_retry_kwargs = options.get("sync_retry_kwargs", self.DEFAULT_SYNC_RETRY_KWARGS)
        AnXinDMATradeGate._read_csv = simple_retry(**_sync_retry_kwargs)(AnXinDMATradeGate._read_csv)

        self._wait_lock_internal = options.get("wait_lock_internal", self.WAIT_LOCK_INTERNAL)
        self._wait_lock_time_out = options.get("wait_lock_time_out", self.WAIT_LOCK_TIME_OUT)

        self._load_orders()

    @property
    def _date(self):
        return Context.get_instance().current_dt.date()

    @property
    def _order_csv(self):
        return os.path.join(self._order_dir, f"algoOrder_{self._date.strftime('%Y%m%d')}.csv")

    @property
    def _cancel_csv(self):
        return os.path.join(self._order_dir, f"algoOrderStop_{self._date.strftime('%Y%m%d')}.csv")

    @property
    def _order_result_csv(self):
        return os.path.join(self._order_dir, f"execResult_{self._date.strftime('%Y%m%d')}.csv")

    @property
    def _order_update_csv(self):
        return os.path.join(self._order_dir, f"orderUpdate_{self._date.strftime('%Y%m%d')}.csv")

    @property
    def _trade_update_csv(self):
        return os.path.join(self._order_dir, f"tradeUpdate_{self._date.strftime('%Y%m%d')}.csv")

    @property
    def _assert_info_csv(self):
        return os.path.join(self._order_dir, f"assetInfo_{self._date.strftime('%Y%m%d')}.csv")

    @property
    def _position_info_csv(self):
        return os.path.join(self._order_dir, f"positionInfo_{self._date.strftime('%Y%m%d')}.csv")
