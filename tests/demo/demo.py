# -#- coding: utf-8 -*-
import datetime


def process_initialize(context):
    log.info("process_initialize run")

    # set_options(
    #     use_account=False,
    # )

    run_daily(func_093000, "09:30:00")
    run_daily(before_market_open, "open-30m")
    run_daily(market_open, "open")
    run_daily(market_close, "close")
    run_daily(func_every_minute, "every_minute")


def func_093000(context):
    log.info("func_093000 run")


def before_market_open(context):
    log.info("before_market_open run")


def market_open(context):
    log.info("market_open run")


def market_close(context):
    log.info("market_close run")


def func_every_minute(context):
    log.info("func_every_minute run")

