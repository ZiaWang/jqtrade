# -*- coding: utf-8 -*-


__options__ = {
    "start": "2023-11-09 08:00:00",
    "end": "2023-11-09 23:00:00",
    "debug": True
}


def process_initialize(context):
    log.info("process_initialize run.")

    run_daily(before_market_open, "open-30m")
    run_daily(market_open, "09:30:30")


def market_open(context):
    log.info("market_open run.")
    order_id = order("000001.XSHE", 100, LimitOrderStyle(11.11))
    assert order_id


def before_market_open(context):
    log.info("before_market_open run.")
    log.info("portfolio: %s" % context.portfolio)

    assert context.portfolio.total_assert == 10000
    assert context.portfolio.available_cash == 5000
    assert context.portfolio.locked_cash == 1000

    assert len(context.portfolio.long_positions) == 1
    assert "000001.XSHE" in context.portfolio.long_positions

    pos = context.portfolio.long_positions["000001.XSHE"]
    assert pos.code == "000001.XSHE"
    assert pos.amount == 1000
    assert pos.available_amount == 100
    assert pos.avg_cost == 11.11

    from jqtrade.account.order import OrderSide
    assert pos.side == OrderSide.long

    assert pos.last_price == 11.10
    assert pos.position_value == 111000
