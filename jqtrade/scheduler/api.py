# -*- coding: utf-8 -*-


class UserContext(object):
    """
    Usage:
        用户策略进程中的context对象，提供一些数据访问接口
    """

    def __init__(self, ctx):
        self.__ctx = ctx

    @property
    def strategy_dt(self):
        """ 策略当前逻辑时间 """
        return self.__ctx.strategy_dt

    @property
    def current_dt(self):
        """ 当前实际物理时间 """
        return self.__ctx.current_dt

    @property
    def portfolio(self):
        """ 账户信息对象，通过此对象访问账户持仓、资金信息 """
        return self.__ctx.portfolio
