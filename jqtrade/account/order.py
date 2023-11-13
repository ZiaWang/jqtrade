# -*- coding: utf-8 -*-
import datetime

from enum import Enum

from ..scheduler.log import sys_logger
from ..scheduler.exceptions import InternalError


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

    # 订单已撤销(部成部撤也使用canceled状态，通过订单的filled_amount、canceled_amount查看成交/撤单数量)
    canceled = "canceled"

    # 订单被废单
    rejected = "rejected"

    @classmethod
    def is_valid_status(cls, status):
        return status in cls.__members__


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
        if not cls.is_valid_side(side):
            raise InternalError("invalid side: %s" % side)
        return cls.long if side == "long" else cls.short


class OrderAction(Enum):
    # 开仓
    open = "open"

    # 平仓
    close = "close"

    @classmethod
    def is_valid_action(cls, action):
        return action in cls.__members__


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
        if style not in ("market", "limit"):
            raise ValueError("invalid style: %s" % style)

        if style == "market":
            return MarketOrderStyle(price)
        else:
            return LimitOrderStyle(price)


class MarketOrderStyle(OrderStyle):
    def __init__(self, price=0):
        super(MarketOrderStyle, self).__init__(price)


class LimitOrderStyle(OrderStyle):
    pass


class AbsOrder(object):

    def on_request_order(self, order_id):
        raise NotImplementedError

    def on_confirmed(self, confirm_id, confirm_dt):
        raise NotImplementedError

    def on_request_cancel(self):
        raise NotImplementedError

    def on_canceled(self, deal_id, amount):
        raise NotImplementedError

    def on_deal(self, deal_id, price, amount, commission=None):
        raise NotImplementedError

    def on_rejected(self, deal_id, err_msg):
        raise NotImplementedError


class Order(AbsOrder):
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
        self._action = action

        # 内部委托id
        self._order_id = order_id

        # 订单状态
        self._status = status

        # 订单类型
        self._style = style

        # 创建时间
        self._create_time = create_time

        # 委托时间
        self._entrust_time = entrust_time

        # 委托方向
        self._side = side

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

    def on_request_order(self, order_id):
        self._order_id = order_id
        self._status = OrderStatus.new
        self._create_time = datetime.datetime.now()

    def on_confirmed(self, confirm_id, confirm_dt):
        self._confirm_id = confirm_id
        self._entrust_time = confirm_dt
        self._status = OrderStatus.open

    def on_request_cancel(self):
        self._status = OrderStatus.canceling

    def on_canceled(self, deal_id, amount):
        self._canceled_amount = amount
        self._status = OrderStatus.canceled

    def on_rejected(self, deal_id, err_msg):
        self._status = OrderStatus.rejected

    def on_deal(self, deal_id, price, amount, commission=None):
        self._filled_amount += amount
        self._deal_balance += price * amount

        if commission:
            self._commission += commission

        self._avg_cost = (self._deal_balance + self._commission) / self._filled_amount

        if self._filled_amount == self._amount:
            self._status = OrderStatus.filled
        else:
            self._status = OrderStatus.filling

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
