# -*- coding: utf-8 -*-
import datetime


def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        account_no="123456",
        order_dir="/Users/wangzihao/jqtrade/data"
    )

    dt = datetime.datetime.now() + datetime.timedelta(seconds=10)

    run_daily(func, dt.strftime("%H:%M:%S"))


def func(context):
    log.info("func run.")
    order("000001.XSHE", 100, LimitOrderStyle(11.11))

    log.info(context.portfolio.total_assert)
    log.info(context.portfolio.locked_cash)
    log.info(context.portfolio.available_cash)
    log.info(context.portfolio.long_positions)
    log.info(context.portfolio.short_positions)
