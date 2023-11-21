# -*- coding: utf-8 -*-
import os
import datetime


def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        account_no="880100000345",
        # account_no="915900000469",
        order_dir="C:\orders",
        coding="GBK",
    )

    log.info("total_assert： %s" % context.portfolio.total_assert)
    log.info("locked_cash： %s" % context.portfolio.locked_cash)
    log.info("available_cash： %s" % context.portfolio.available_cash)
    log.info("long_positions length:  %s" % len(context.portfolio.long_positions))
    log.info("short_positions length： %s" % len(context.portfolio.short_positions))

    # run_daily(do_order, (datetime.datetime.now() + datetime.timedelta(seconds=10)).strftime("%H:%M:%S"))
    run_daily(do_cancel, (datetime.datetime.now() + datetime.timedelta(seconds=11)).strftime("%H:%M:%S"))
    run_daily(check_orders, (datetime.datetime.now() + datetime.timedelta(seconds=20)).strftime("%H:%M:%S"))


g = {}


def do_order(context):
    log.info("do_order run.")

    # order_id = order("300248.XSHE", 300, LimitOrderStyle(10.20))
    # order_id = order("300248.XSHE", 400, MarketOrderStyle())

    order_id = order("300248.XSHE", 2300, LimitOrderStyle(10.10))
    log.info("用户下单，order id：%s" % order_id)

    g["order_id"] = order_id


def do_cancel(context):
    log.info("cancel_order run.")


def check_orders(context):
    log.info("check_orders run.")
    for _order in get_orders():
        log.info("查询到本地订单：%s" % _order._UserOrder__order.__dict__)
