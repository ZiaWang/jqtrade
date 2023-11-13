# -*- coding: utf-8 -*-
from .api import UserPosition


class Portfolio(object):
    """ 账户资金/持仓信息聚合类 """

    def __init__(self, account):
        self.__account = account

    @property
    def long_positions(self):
        positions = {}
        for _code, _pos in self.__account.long_positions.items():
            positions[_code] = UserPosition(_pos)
        return positions

    @property
    def short_positions(self):
        positions = {}
        for _code, _pos in self.__account.short_positions.items():
            positions[_code] = UserPosition(_pos)
        return positions

    @property
    def total_assert(self):
        return self.__account.total_assert

    @property
    def available_cash(self):
        return self.__account.available_cash

    @property
    def locked_cash(self):
        return self.__account.locked_cash

    def __str__(self):
        return "Portfolio(total_assert=%s, available_assert=%s, locked_cash=%s, " \
               "long_positions=%s, short_positions=%s)" % (self.total_assert, self.available_cash, self.locked_cash,
                                                           self.long_positions, self.short_positions)
