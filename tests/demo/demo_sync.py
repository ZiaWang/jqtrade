# -*- coding: utf-8 -*-
import datetime


def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        account_no="880300017401",
        order_dir="C:\Ax\安信OneQuant\csvTemplate\DMA算法",
    )

    log.info(f"total_assert： {context.portfolio.total_assert}")
    log.info(f"locked_cash： {context.portfolio.locked_cash}")
    log.info(f"available_cash： {context.portfolio.available_cash}")
    log.info(f"long_positions length:  {len(context.portfolio.long_positions)}")
    log.info(f"short_positions length： {len(context.portfolio.short_positions)}")

    run_daily(check_sync_balance, (datetime.datetime.now() + datetime.timedelta(seconds=10)).strftime("%H:%M:%S"))
    run_daily(check_sync_orders, (datetime.datetime.now() + datetime.timedelta(seconds=30)).strftime("%H:%M:%S"))


def check_sync_balance(context):
    log.info("check_sync_account run.")

    sync_balance()

    log.info(f"total_assert： {context.portfolio.total_assert}")
    log.info(f"locked_cash： {context.portfolio.locked_cash}")
    log.info(f"available_cash： {context.portfolio.available_cash}")
    log.info(f"long_positions length:  {len(context.portfolio.long_positions)}")
    log.info(f"short_positions length： {len(context.portfolio.short_positions)}")

    for _code, _pos in context.portfolio.long_positions.items():
        log.info(f"long pos: {_code}, {_pos}")

    for _code, _pos in context.portfolio.short_positions.items():
        log.info(f"short pos: {_code}, {_pos}")


def check_sync_orders(context):
    log.info("check_sync_orders run.")
    sync_orders()

    for _order in get_orders():
        log.info("UserOrder: %s" % _order)
