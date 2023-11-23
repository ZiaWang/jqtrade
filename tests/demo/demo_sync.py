# -*- coding: utf-8 -*-
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

    run_daily(check_sync_balance, (datetime.datetime.now() + datetime.timedelta(seconds=10)).strftime("%H:%M:%S"))
    run_daily(check_sync_orders, (datetime.datetime.now() + datetime.timedelta(seconds=30)).strftime("%H:%M:%S"))


def check_sync_balance(context):
    log.info("check_sync_account run.")

    sync_balance()
    log.info("total_assert： %s" % context.portfolio.total_assert)
    log.info("locked_cash： %s" % context.portfolio.locked_cash)
    log.info("available_cash： %s" % context.portfolio.available_cash)
    log.info("long_positions length:  %s" % len(context.portfolio.long_positions))
    log.info("short_positions length： %s" % len(context.portfolio.short_positions))


def check_sync_orders(context):
    log.info("check_sync_orders run.")
    sync_orders()

    for _order in get_orders():
        log.info("UserOrder: %s" % _order)
