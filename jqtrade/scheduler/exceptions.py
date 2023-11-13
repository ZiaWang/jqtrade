# -*- coding: utf-8 -*-


class UserError(Exception):
    """ 用户异常基类 """
    pass


class InternalError(Exception):
    """ 系统异常基类 """
    pass


class RepeatedTask(UserError):
    """ 用户启动重复实盘错误 """
    pass


class InvalidCall(UserError):
    """ 用户调用错误 """
    pass


class InvalidParam(UserError):
    """ 用户参数错误 """
    pass


class ConfigError(InternalError):
    """ 配置错误 """
    pass
