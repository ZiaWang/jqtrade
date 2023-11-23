# -*- coding: utf-8 -*-
import datetime


def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        account_no="880300017401",
        order_dir="C:\Ax\安信OneQuant\csvTemplate\DMA算法",
        file_encoding="GBK",
        sync_period=[
                    # (datetime.time(11), datetime.time(11, 30)),
                    ("11:20:00", "11:40:00"),
                    # (datetime.time(13, 0), datetime.time(15, 0)),
                ],
        sync_internal=10,
    )

    log.info("total_assert： %s" % context.portfolio.total_assert)
    log.info("locked_cash： %s" % context.portfolio.locked_cash)
    log.info("available_cash： %s" % context.portfolio.available_cash)
    log.info("long_positions length:  %s" % len(context.portfolio.long_positions))
    log.info("short_positions length： %s" % len(context.portfolio.short_positions))

    run_daily(cancel_open_orders, (datetime.datetime.now() + datetime.timedelta(seconds=1)).strftime("%H:%M:%S"))
    run_daily(do_order, (datetime.datetime.now() + datetime.timedelta(seconds=5)).strftime("%H:%M:%S"))
    run_daily(do_cancel, (datetime.datetime.now() + datetime.timedelta(seconds=15)).strftime("%H:%M:%S"))

    run_daily(check_orders, (datetime.datetime.now() + datetime.timedelta(seconds=20)).strftime("%H:%M:%S"))

    run_daily(check_sync_balance, (datetime.datetime.now() + datetime.timedelta(seconds=25)).strftime("%H:%M:%S"))
    run_daily(check_sync_orders, (datetime.datetime.now() + datetime.timedelta(seconds=30)).strftime("%H:%M:%S"))

    # run_daily(report_order_status, "every_minute")


g = {
    # "code": "601988.XSHG",
    "code": "511880.XSHG",
    "price": 101.753,
    "amount": -100,
}


def do_order(context):
    log.info("do_order run.")

    log.info(f"pos before trade: {context.portfolio.long_positions.get(g['code'])}")
    order_id = order(g['code'], g['amount'], LimitOrderStyle(g['price']))
    log.info(f"用户下单，order id：{order_id}")
    log.info(f"pos after trade: {context.portfolio.long_positions.get(g['code'])}")

    g["order_id"] = order_id


def do_cancel(context):
    log.info("cancel_order run.")
    cancel_order(g["order_id"])


def check_orders(context):
    log.info("check_orders run.")
    for _order in get_orders():
        log.info(f"get_order：{_order._UserOrder__order.__dict__}")

    log.info(f"pos: {context.portfolio.long_positions.get(g['code'])}")


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
        log.info(f"UserOrder: {_order}")


def report_order_status(context):
    log.info("report_order_status run.")

    if "order_id" in g:
        log.info(get_orders(order_id=g["order_id"])[0]._UserOrder__order.__dict__)


def cancel_open_orders(context):
    log.info("cancel_open_orders run.")
    for _order in get_orders():
        if _order.status.value in ("new", "open"):
            cancel_order(_order.order_id)
