# -*- coding: utf-8 -*-
import datetime


def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        account_no="880300017401",
        order_dir="C:\Ax\安信OneQuant\csvTemplate\DMA算法",
        file_encoding="GBK",
        sync_internal=2,
    )

    log.info("total_assert： %s" % context.portfolio.total_value)
    log.info("locked_cash： %s" % context.portfolio.locked_cash)
    log.info("available_cash： %s" % context.portfolio.available_cash)
    log.info("long_positions length:  %s" % len(context.portfolio.long_positions))
    log.info("short_positions length： %s" % len(context.portfolio.short_positions))

    run_daily(do_order, (datetime.datetime.now() + datetime.timedelta(seconds=5)).strftime("%H:%M:%S"))
    run_daily(do_cancel, (datetime.datetime.now() + datetime.timedelta(seconds=15)).strftime("%H:%M:%S"))
    run_daily(check_orders, (datetime.datetime.now() + datetime.timedelta(seconds=30)).strftime("%H:%M:%S"))


g = {}


def do_order(context):
    log.info("do_order run.")

    log.info("pos before trade: %s" % (context.portfolio.long_positions["000001.XSHE"]))
    log.info("pos before trade: %s" % (context.portfolio.long_positions["511880.XSHG"]))

    order_ids = batch_submit_orders([
        {
            "code": "511880.XSHG",
            "amount": 200,
            "style": LimitOrderStyle(101.770),
        },
        {
            "code": "511880.XSHG",
            "amount": 100,
            "style": LimitOrderStyle(101.770),
        }
    ])

    log.info("用户下单，order id：%s" % order_ids)
    log.info("pos after trade: %s" % (context.portfolio.long_positions["511880.XSHG"]))


def do_cancel(context):
    log.info("cancel_order run.")

    order_ids = []
    for _order_id, _order in get_orders().items():
        if _order.status in ("new", "open"):
            order_ids.append(_order_id)

    batch_cancel_orders(order_ids)


def check_orders(context):
    log.info("check_orders run.")
    for _order in get_orders().values():
        log.info("UserOrder：%s" % _order._UserOrder__order.__dict__)

    log.info(f"check_orders pos: {context.portfolio.long_positions['511880.XSHG']}")
