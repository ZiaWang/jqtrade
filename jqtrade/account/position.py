# -*- coding: utf-8 -*-


class AbsPosition(object):

    def on_deal(self, price, amount):
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
