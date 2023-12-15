# -*- coding: utf-8 -*-
from .order import OrderAction


class AbsPosition(object):

    def on_order_created(self, order):
        raise NotImplementedError

    def on_order_rejected(self, order):
        raise NotImplementedError


class Position(AbsPosition):
    def __init__(self, code, amount, available_amount, avg_cost, side, **kwargs):

        # 持仓标的代码
        self._code = code

        # 持仓数量
        self._amount = amount

        # 可用数量
        self._available_amount = available_amount

        # 持仓成本
        self._avg_cost = avg_cost

        # 持仓方向
        self._side = side

        # 标的最新价格
        self._last_price = kwargs.get("last_price", None)

        # 持仓市值
        self._position_value = kwargs.get("position_value", None)

    def on_order_created(self, order):
        # 订单平仓时，调整持仓可用数量，避免用户下超，方便用户查询到当前可用数量，等sync_balance同步回有些延迟
        if order.action == OrderAction.close:
            self._available_amount = max(self._available_amount - order.amount, 0)

    def on_order_rejected(self, order):
        # 平仓单被拒绝时，不尝试调整可用数量，因为同步订单之前会同步持仓，这里处理可用数量可能会将用户刚下的同标的单子冻结数量释放掉
        pass

    def on_deal(self, price, amount):
        # 全量同步，do nothing
        pass

    @property
    def code(self):
        return self._code

    @property
    def amount(self):
        return self._amount

    @property
    def available_amount(self):
        return self._available_amount

    @property
    def locked_amount(self):
        return self._amount - self._available_amount

    @property
    def avg_cost(self):
        return self._avg_cost

    @property
    def side(self):
        return self._side

    @property
    def last_price(self):
        return self._last_price

    @property
    def position_value(self):
        return self._position_value
