# -*- coding: utf-8 -*-

import sys
import logging
import datetime


class SystemLogFormatter(logging.Formatter):
    converter = datetime.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s


# default format
fmt = '[%(asctime)s] [%(levelname)s] [%(process)d] [%(name)s] %(message)s'


def setup_logger(level="INFO"):
    """ 设置标准输出日志 """

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(SystemLogFormatter(fmt, datefmt='%Y-%m-%d %H:%M:%S.%f'))
    logging.getLogger().addHandler(stdout_handler)

    # stderr_handler = logging.StreamHandler(stream=sys.stderr)
    # stderr_handler.setFormatter(SystemLogFormatter(fmt, datefmt='%Y-%m-%d %H:%M:%S.%f'))
    # stderr_handler.setLevel('ERROR')
    # logging.getLogger().addHandler(stderr_handler)

    logging.getLogger().setLevel(level)


def setup_file_logger(file, level="INFO"):
    """ 设置文件输出日志 """

    file_handler = logging.FileHandler(file)
    file_handler.setFormatter(SystemLogFormatter(fmt, datefmt='%Y-%m-%d %H:%M:%S.%f'))
    file_handler.setLevel(level)

    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(level)


def set_log_context(context):
    """ 设置日志的context，目前仅增加STRATEGY_DT，方便在测试用例中查看逻辑时间 """

    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.strategy_dt = context.strategy_dt
            return True

    strategy_fmt = '[%(asctime)s] [%(levelname)s] [%(process)d] [%(name)s] [STRATEGY_DT=%(strategy_dt)s] %(message)s'
    formatter = SystemLogFormatter(strategy_fmt, datefmt='%Y-%m-%d %H:%M:%S,%f')
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())


sys_logger = logging.getLogger("system")

user_logger = logging.getLogger("user")
