# -*- coding: utf-8 -*-
import os
import datetime


def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        # account_no="880100000345",
        account_no="915900000469",
        order_dir="C:\orders",
        coding="GBK",
    )

    log.info("total_assert： %s" % context.portfolio.total_assert)
    log.info("locked_cash： %s" % context.portfolio.locked_cash)
    log.info("available_cash： %s" % context.portfolio.available_cash)
    log.info("long_positions length:  %s" % len(context.portfolio.long_positions))
    log.info("short_positions length： %s" % len(context.portfolio.short_positions))

    now = datetime.datetime.now()
    for i in range(20):
        order_dt = now + datetime.timedelta(minutes=i, seconds=0)
        cancel_dt = now + datetime.timedelta(minutes=i, seconds=30)
        run_daily(do_order, order_dt.strftime("%H:%M:%S"))
        run_daily(do_cancel, cancel_dt.strftime("%H:%M:%S"))


g = {}


def do_order(context):
    log.info("do_order run.")

    order_id = order("300248.XSHE", 100, LimitOrderStyle(10.0))
    log.info("用户下单，order id：%s" % order_id)
    g["order_id"] = order_id


def do_cancel(context):
    log.info("do_cancel run.")

    if "order_id" in g:
        cancel_order(g["order_id"])
