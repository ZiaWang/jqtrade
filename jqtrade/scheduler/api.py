# -*- coding: utf-8 -*-


class UserContext(object):
    """ 用户策略进程中的context对象 """

    def __init__(self, ctx):
        self.__ctx = ctx

    @property
    def strategy_dt(self):
        return self.__ctx.strategy_dt

    @property
    def current_dt(self):
        return self.__ctx.current_dt

    @property
    def portfolio(self):
        return self.__ctx.portfolio
