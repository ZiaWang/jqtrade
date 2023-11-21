# -*- coding: utf-8 -*-
from ..scheduler.exceptions import InvalidParam, InvalidCall
from ..scheduler.context import Context
from ..scheduler.log import sys_logger

from .order import OrderSide, OrderStatus, OrderStyle, MarketOrderStyle, LimitOrderStyle


logger = sys_logger.getChild("account.api")


def _check_code(code):
    if not (code[-4:] in ("XSHE", "XSHG") or code[:-5].isdigit()):
        raise InvalidParam("标的代码错误: %s" % code)


def _check_amount(amount):
    if not isinstance(amount, int) or amount == 0:
        raise InvalidParam("委托数量错误，只能是非零整数：%s" % amount)


def _check_style(style):
    if not OrderStyle.is_valid_style(style):
        raise InvalidParam("style参数错误，只能是MarketOrderStyle, LimitOrderStyle类型的实例: %s" % style)


def _check_side(side):
    if not OrderSide.is_valid_side(side):
        raise InvalidParam("side参数错误，只能是long或short")


def _check_status(status):
    if not OrderStatus.is_valid_status(status):
        raise InvalidParam("status参数错误，只能是%s中的一种" % list(OrderStatus.__members__))


def order(code, amount, style=None, side='long'):
    """ 下单

    Args:
        code: 标的代码字符串
        amount: 委托数量，正数代表买入、负数代表卖出
        style: 下单类型，支持MarketOrderStyle、LimitOrderStyle
        side: 买卖方向，做多：'long'，做空：'short'

    Return:
        返回内部委托id字符串
    """
    _check_code(code)
    _check_amount(amount)

    if style:
        _check_style(style)
    else:
        style = MarketOrderStyle(0)

    if side:
        _check_side(side)
    else:
        side = "long"

    side = OrderSide.long if side == "long" else OrderSide.short

    ctx = Context.get_instance()
    order_id = ctx.account.order(code, amount, style, side)
    return order_id


def cancel_order(order_id):
    order_id = str(order_id)

    account = Context.get_instance().account
    account.cancel_order(order_id)


def get_orders(order_id=None, code=None, status=None):
    if code:
        _check_code(code)

    if status:
        _check_status(status)

    acc_orders = Context.get_instance().account.orders

    orders = acc_orders.values()
    if order_id:
        order_id = str(order_id)
        orders = [acc_orders[order_id], ] if order_id in acc_orders else []

    if code:
        orders = [o for o in orders if o.code == code]

    if status:
        orders = [o for o in orders if o.status.value == status]

    return [UserOrder(_order) for _order in orders]


def batch_submit_orders(orders):
    account = Context.get_instance().account

    order_ids = []
    for _order_info in orders:
        _code = _order_info.get("code")
        _amount = _order_info.get("amount")
        _style = _order_info.get("style")
        _side = _order_info.get("side")

        try:
            if _code is None:
                raise InvalidParam("批量单缺少标的代码字段code，请检查批量单信息: %s" % _order_info)
            else:
                _check_code(_code)
            if _amount is None:
                raise InvalidParam("批量单缺少标的代码字段amount，请检查批量单信息: %s" % _order_info)
            else:
                _check_amount(_amount)
            if _style:
                _check_style(_style)
            if _side:
                _check_side(_side)

            _order_id = account.order(_code, _amount, _style, _style)
        except InvalidParam as e:
            sys_logger.error("忽略批量单中的异常订单：%s，异常原因：%s" % (_order_info, e))
            _order_id = None

        # TODO: 考虑下内部异常是否需要捕获

        order_ids.append(_order_id)
    return order_ids


def batch_cancel_orders(order_ids):
    account = Context.get_instance().account

    for _order_id in order_ids:
        account.cancel_order(_order_id)


def sync_balance():
    Context.get_instance().account.sync_balance()


def sync_orders():
    Context.get_instance().account.sync_orders()


class UserOrder(object):
    def __init__(self, sys_order):
        self.__order = sys_order
    
    @property
    def code(self):
        return self.__order.code
    
    @property
    def status(self):
        return self.__order.status
    
    @property
    def side(self):
        return self.__order.side
    
    @property
    def price(self):
        return self.__order.price

    @property
    def amount(self):
        return self.__order.amount

    @property
    def avg_cost(self):
        return self.__order.avg_cost

    @property
    def action(self):
        return self.__order.action

    @property
    def order_id(self):
        return self.__order.order_id
    
    @property
    def commission(self):
        return self.__order.commission


class UserPosition(object):
    def __init__(self, sys_position):
        self.__position = sys_position

    @property
    def code(self):
        return self.__position.code

    @property
    def amount(self):
        return self.__position.amount

    @property
    def locked_amount(self):
        return self.__position.locked_amount

    @property
    def available_amount(self):
        return self.__position.available_amount

    @property
    def avg_cost(self):
        return self.__position.avg_cost

    hold_cost = avg_cost

    @property
    def side(self):
        return self.__position.side

    @property
    def last_price(self):
        return self.__position.last_price

    @property
    def position_value(self):
        return self.__position.position_value

    def __str__(self):
        return "UserPosition(code=%s, amount=%s, locked_amount=%s, available_amount=%s, avg_code=%s, " \
               "side=%s, last_price=%s, position_value=%s)" % (self.code, self.amount, self.locked_amount,
                                                               self.available_amount, self.avg_cost, self.side,
                                                               self.last_price, self.position_value)

    def __repr__(self):
        return self.__str__()


__all__ = [
    "LimitOrderStyle", "MarketOrderStyle",
    "order", "cancel_order",
    "batch_submit_orders", "batch_cancel_orders",
    "get_orders",
    "sync_balance", "sync_orders",
]
