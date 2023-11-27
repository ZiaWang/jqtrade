# -*- coding: utf-8 -*-
import datetime

from enum import Enum

from ..common.log import sys_logger
from ..common.utils import parse_dt


logger = sys_logger.getChild("account.order")


class OrderStatus(Enum):
    # 用户提交委托订单，尚未收到柜台委托确认
    new = "new"

    # 订单收到委托确认
    open = "open"

    # 订单部分成交
    filling = "filling"

    # 订单全部成交
    filled = "filled"

    # 订单撤销中
    canceling = "canceling"

    # 部成部撤
    partly_canceled = "partly_canceled"

    # 订单已撤销
    canceled = "canceled"

    # 订单被废单
    rejected = "rejected"

    @classmethod
    def is_valid_status(cls, status):
        return status in cls.__members__

    @classmethod
    def finished_status(cls):
        return cls.filled, cls.partly_canceled, cls.canceled, cls.rejected

    @classmethod
    def get_status(cls, status):
        if isinstance(status, cls):
            return status

        try:
            return cls.__members__[status]
        except KeyError:
            raise ValueError(f"bad status: {status}")


class OrderSide(Enum):
    # 多仓
    long = "long"

    # 空仓
    short = "short"

    @classmethod
    def is_valid_side(cls, side):
        return side in cls.__members__

    @classmethod
    def get_side(cls, side):
        if isinstance(side, cls):
            return side

        try:
            return cls.__members__[side]
        except KeyError:
            raise ValueError(f"invalid side: {side}")


class OrderAction(Enum):
    # 开仓
    open = "open"

    # 平仓
    close = "close"

    @classmethod
    def is_valid_action(cls, action):
        return action in cls.__members__

    @classmethod
    def get_action(cls, action):
        if isinstance(action, cls):
            return action

        try:
            return cls.__members__[action]
        except KeyError:
            raise ValueError(f"bad action: {action}")


class OrderStyle(object):
    def __init__(self, price):
        self._price = price

    @property
    def price(self):
        return self._price

    @classmethod
    def is_valid_style(cls, style):
        return isinstance(style, (MarketOrderStyle, LimitOrderStyle))

    @classmethod
    def get_style(cls, style, price):
        if isinstance(style, cls):
            return style

        if style not in ("market", "limit"):
            raise ValueError(f"invalid style: {style}")

        if style == "market":
            return MarketOrderStyle(price)
        else:
            return LimitOrderStyle(price)

    def __str__(self):
        return f"{self.__class__.__name__}(price={self._price})"


class MarketOrderStyle(OrderStyle):
    def __init__(self, price=0):
        super(MarketOrderStyle, self).__init__(price)

    @property
    def value(self):
        return "market"


class LimitOrderStyle(OrderStyle):
    @property
    def value(self):
        return "limit"


class Order(object):
    def __init__(self, code, price, amount, action,
                 order_id=None, status=None, style=None, create_time=None, entrust_time=None,
                 side=OrderSide.long,
                 **kwargs):

        # 订单标的代码
        self._code = code

        # 订单委托价格
        self._price = price

        # 订单委托量
        self._amount = amount

        # 订单行为，开仓 or 平仓
        self._action = OrderAction.get_action(action)

        # 内部委托id
        self._order_id = order_id

        # 订单状态
        self._status = OrderStatus.get_status(status) if status else None

        # 订单类型
        self._style = OrderStyle.get_style(style, price) if style else None

        # 创建时间
        self._create_time = parse_dt(create_time) if create_time else None

        # 委托时间
        self._entrust_time = parse_dt(entrust_time) if entrust_time else None

        # 委托方向
        self._side = OrderSide.get_side(side) if style else None

        # 券商返回的委托号
        self._confirm_id = kwargs.get("confirm_id", None)

        # 已成交数量
        self._filled_amount = kwargs.get("filled_amount", 0)

        # 撤单数量
        self._canceled_amount = kwargs.get("canceled_amount", 0)

        # 成交额
        self._deal_balance = kwargs.get("deal_balance", 0)

        # 平均成本
        self._avg_cost = kwargs.get("avg_cost", None)

        # 手续费
        self._commission = kwargs.get("commission", 0)

        # 异常信息
        self._err_msg = kwargs.get("err_msg", "")

    def json(self):
        return {
            "code": self._code,
            "price": self._price,
            "amount": self._amount,
            "action": self._action.value,
            "order_id": self._order_id,
            "status": self._status.value,
            "style": self._style.value,
            "create_time": self._create_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "entrust_time": self._entrust_time.strftime("%Y-%m-%d %H:%M:%S.%f") if self._entrust_time else None,
            "side": self._side.value,
            "confirm_id": self._confirm_id,
            "filled_amount": self._filled_amount,
            "canceled_amount": self._canceled_amount,
            "deal_balance": self._deal_balance,
            "avg_cost": self._avg_cost,
            "commission": self._commission,
            "err_msg": self._err_msg,
        }

    @classmethod
    def load(cls, **kwargs):
        return cls(**kwargs)

    @property
    def order_id(self):
        return self._order_id

    @property
    def confirm_id(self):
        return self._confirm_id

    @property
    def code(self):
        return self._code

    @property
    def amount(self):
        return self._amount

    @property
    def price(self):
        return self._price

    @property
    def action(self):
        return self._action

    @property
    def side(self):
        return self._side

    @property
    def status(self):
        return self._status

    @property
    def create_time(self):
        return self._create_time

    @property
    def entrust_time(self):
        return self._entrust_time

    @property
    def avg_cost(self):
        return self._avg_cost

    @property
    def filled_amount(self):
        return self._filled_amount

    @property
    def deal_balance(self):
        return self._deal_balance

    @property
    def canceled_amount(self):
        return self._canceled_amount

    @property
    def style(self):
        return self._style

    @property
    def commission(self):
        return self._commission

    @property
    def err_msg(self):
        return self._err_msg

    def has_finished(self):
        return self._status in OrderStatus.finished_status()

    def on_rejected(self, msg):
        self._status = OrderStatus.rejected
        self._err_msg = msg

    def __eq__(self, other):
        return (
            self._status == other.status
            and self._confirm_id == other.confirm_id
            and self._filled_amount == other.filled_amount
            and self._canceled_amount == other.canceled_amount
            and self._deal_balance == other.deal_balance
            and self._avg_cost == other.avg_cost
            and self._commission == other.commission
        )
