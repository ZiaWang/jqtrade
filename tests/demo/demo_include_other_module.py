# -#- coding: utf-8 -*-

from custom_pkg.utils import hello
from custom_pkg import data


def process_initialize(context):
    log.info("process_initialize run")
    run_daily(func_every_minute, "every_minute")


def func_every_minute(context):
    log.info("market_open run")

    hello()

    log.info("data = %s" % data)
    log.info("data.val = %s" % data.val)
