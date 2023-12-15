# -*- coding: utf-8 -*-
from .order import OrderSide
from .api import UserPosition, UserPositionDict


class Portfolio(object):
    """ 账户资金/持仓信息聚合类 """

    def __init__(self, account):
        self.__account = account

    @property
    def long_positions(self):
        positions = UserPositionDict(OrderSide.long)
        for _code, _pos in self.__account.long_positions.items():
            positions[_code] = UserPosition(_pos)
        return positions

    positions = long_positions

    @property
    def short_positions(self):
        positions = UserPositionDict(OrderSide.short)
        for _code, _pos in self.__account.short_positions.items():
            positions[_code] = UserPosition(_pos)
        return positions

    @property
    def total_value(self):
        return self.__account.total_assert

    @property
    def available_cash(self):
        return self.__account.available_cash

    @property
    def locked_cash(self):
        return self.__account.locked_cash

    @property
    def position_value(self):
        return sum(_pos.position_value for _pos in self.long_positions)

    def __str__(self):
        return f"Portfolio(total_assert={self.total_value}, available_assert={self.available_cash}, " \
               f"locked_cash={self.locked_cash}, long_positions={self.long_positions}, " \
               f"short_positions={self.short_positions}"
