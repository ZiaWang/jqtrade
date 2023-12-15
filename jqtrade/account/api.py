# -*- coding: utf-8 -*-
from ..common.exceptions import InvalidParam
from ..common.log import sys_logger
from ..scheduler.context import Context

from .order import OrderSide, OrderStatus, OrderStyle, MarketOrderStyle, LimitOrderStyle
from .position import Position


logger = sys_logger.getChild("account.api")


def _check_code(code):
    if not (code[-4:] in ("XSHE", "XSHG") and code[:-5].isdigit()):
        raise InvalidParam(f"标的代码错误: {code}")


def _check_amount(amount):
    if not isinstance(amount, int) or amount == 0:
        raise InvalidParam(f"委托数量错误，只能是非零整数：{amount}")


def _check_style(style):
    if not OrderStyle.is_valid_style(style):
        raise InvalidParam(f"style参数错误，只能是MarketOrderStyle, LimitOrderStyle类型的实例: {style}")


def _check_side(side):
    if not OrderSide.is_valid_side(side):
        raise InvalidParam(f"side参数错误，只能是{list(OrderSide.__members__)}中的一种")


def _check_status(status):
    if not OrderStatus.is_valid_status(status):
        raise InvalidParam(f"status参数错误，只能是{list(OrderStatus.__members__)}中的一种")


def order(code, amount, style=None, side='long'):
    """ 下单

    Args:
        code: 标的代码字符串，暂只支持上交所和深交所标的下单
            上交所示例：600000.XSHG
            深交所示例：000001.XSHE
        amount: 委托数量，正数代表买入、负数代表卖出
        style: 下单类型，支持MarketOrderStyle（市价单）、LimitOrderStyle（限价单）
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

    side = OrderSide.get_side(side)

    ctx = Context.get_instance()
    order_id = ctx.account.order(code, amount, style, side)
    return order_id


def cancel_order(order_id):
    """ 撤单

    Args:
        order_id: 内部委托id字符串（order函数返回值）
    """
    order_id = str(order_id)

    account = Context.get_instance().account
    account.cancel_order(order_id)


def get_orders(order_id=None, code=None, status=None):
    """ 查询订单信息

    Args:
        order_id: 内部委托id，查询指定内部id的委托
        code: 标的代码字符串，查询指定标的的委托
        status: 订单状态字符串或OrderStatus类型值，查询指定状态的委托
            status支持：new、open、filling、filled、canceling、partly_canceled、canceled、rejected

    Return:
        返回一个UserOrder对象组成的列表，每一个UserOrder对象对应一笔委托订单。

    Notice:
        order_id, code, status可以一起组合使用，相当于查询过滤条件（与条件）
    """
    if code:
        _check_code(code)

    if status:
        if isinstance(status, OrderStatus):
            status = status.value
        else:
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

    return {_order.order_id: UserOrder(_order) for _order in orders}


def batch_submit_orders(orders):
    """ 批量下单

    Args:
        orders: 列表类型，列表中每一个元素对应一个字典，存放订单信息
            每个字典中：
                必须提供：code、amount
                可选提供：style、side

    Return:
        返回一个列表，存放内部订单id字符串（通order函数返回值）
        如果批量单中某笔订单委托柜台失败，就会返回None
    """
    order_ids = []
    for _order_info in orders:
        _code = _order_info.get("code")
        _amount = _order_info.get("amount")
        _style = _order_info.get("style")
        _side = _order_info.get("side")

        try:
            if _code is None:
                raise InvalidParam(f"批量单缺少标的代码字段code，请检查订单信息: {_order_info}")

            if _amount is None:
                raise InvalidParam(f"批量单缺少标的代码字段amount，请检查订单信息: {_order_info}")

            _order_id = order(_code, _amount, _style, _side)
        except Exception as e:
            sys_logger.error(f"批量单下单时发现有异常订单：{_order_info}，异常原因：{e}")
            _order_id = None

        order_ids.append(_order_id)
    return order_ids


def batch_cancel_orders(order_ids):
    """ 批量撤单

    Args:
        order_ids: 列表，每一个元素是一个内部委托id字符串，用于撤单
    """
    for _order_id in order_ids:
        cancel_order(_order_id)


def sync_balance():
    Context.get_instance().account.sync_balance()


def sync_orders():
    Context.get_instance().account.sync_orders()


class _UserObject(object):

    def __repr__(self):
        return self.__str__()


class UserOrder(object):
    def __init__(self, sys_order):
        self.__order = sys_order
    
    @property
    def code(self):
        return self.__order.code
    
    @property
    def status(self):
        return self.__order.status.value
    
    @property
    def side(self):
        return self.__order.side.value

    @property
    def style(self):
        return self.__order.style

    @property
    def order_price(self):
        return self.__order.price

    @property
    def amount(self):
        return self.__order.amount

    @property
    def filled_amount(self):
        return self.__order.filled_amount

    @property
    def avg_price(self):
        return self.__order.avg_cost

    @property
    def action(self):
        return self.__order.action.value

    @property
    def order_id(self):
        return self.__order.order_id
    
    @property
    def commission(self):
        return self.__order.commission

    @property
    def err_msg(self):
        return self.__order.err_msg

    @property
    def canceled_amount(self):
        return self.__order.canceled_amount

    @property
    def create_time(self):
        return self.__order.create_time

    @property
    def entrust_time(self):
        return self.__order.entrust_time

    @property
    def deal_balance(self):
        return self.__order.deal_balance

    def __str__(self):
        return f"UserOrder(order_id={self.order_id}, code={self.code}, amount={self.amount}, " \
               f"style={self.style}), status={self.status}, action={self.action}, side={self.side}, " \
               f"filled_amount={self.filled_amount}, avg_price={self.avg_price}, deal_balance={self.deal_balance}, " \
               f"canceled_amount={self.canceled_amount}, create_time={self.create_time}"


class UserPositionDict(dict):
    
    def __init__(self, side, *args, **kwargs):
        super(UserPositionDict, self).__init__(*args, **kwargs)
        self._side = side
    
    def __getitem__(self, code):
        try:
            return dict.__getitem__(self, code)
        except KeyError:
            sys_logger.warn(f"{code} 在 positions 中不存在，我们返回空的 Position 对象, "
                            f"total_amount/closeable_amount/avg_cost/acc_avg_cost/position_value/last_price 都是 0")
            return UserPosition.get_empty_pos(code, side=self._side)


class UserPosition(object):
    def __init__(self, sys_position):
        self.__position = sys_position

    @classmethod
    def get_empty_pos(cls, code, side):
        return UserPosition(Position(code, 0, 0, 0, side, position_value=0, last_price=0))

    @property
    def security(self):
        return self.__position.code

    @property
    def total_amount(self):
        return self.__position.amount

    @property
    def closeable_amount(self):
        return self.__position.available_amount

    @property
    def avg_cost(self):
        return self.__position.avg_cost

    acc_avg_cost = avg_cost

    @property
    def side(self):
        if self.__position.side:
            return self.__position.side.value

    @property
    def last_price(self):
        return self.__position.last_price

    price = last_price

    @property
    def position_value(self):
        return self.__position.position_value

    value = position_value

    def __str__(self):
        return f"UserPosition(security={self.security}, total_amount={self.total_amount}, " \
               f"closeable_amount={self.closeable_amount}, avg_cost={self.avg_cost}, side={self.side}, " \
               f"last_price={self.last_price}, position_value={self.position_value})"


__all__ = [
    "LimitOrderStyle", "MarketOrderStyle",
    "order", "cancel_order",
    "batch_submit_orders", "batch_cancel_orders",
    "get_orders",
    "sync_balance", "sync_orders",
]
