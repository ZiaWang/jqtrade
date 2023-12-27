# -#- coding: utf-8 -*-


__options__ = {
    "start": "2023-10-30 08:00:00",
    "end": "2023-10-31",
    "debug": True
}


def process_initialize(context):
    log.info("process_initialize run")
    run_daily(before_market_open, "open-30m")
    run_daily(market_open, "open")
    run_daily(market_close, "close")
    run_daily(func_every_minute, "every_minute")


def process_exit(context):
    log.info("process_exit run")


def before_market_open(context):
    log.info("before_market_open run")


def market_open(context):
    log.info("market_open run")


def market_close(context):
    log.info("market_close run")


def func_every_minute(context):
    log.info("func_every_minute run")

