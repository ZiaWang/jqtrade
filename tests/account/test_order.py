# -*- coding: utf-8 -*-
import datetime

from jqtrade.account.order import Order, OrderSide, OrderStyle, OrderAction, \
    OrderStatus, MarketOrderStyle, LimitOrderStyle


def test_order_instance():
    order_info = {
        "code": "000001.XSHE",
        "price": 11.11,
        "amount": 1000,
        "action": OrderAction.open,
        "order_id": "2333333",
        "status": OrderStatus.canceled,
        "style": LimitOrderStyle(11.11),
        "create_time": datetime.datetime(2023, 11, 7, 13, 10, 33),
        "entrust_time": datetime.datetime(2023, 11, 7, 13, 10, 33, 500),
        "side": OrderSide.long,

        "avg_cost": 11.115,
        "filled_amount": 800,
        "deal_balance": 8890,
        "canceled_amount": 200,
    }
    order1 = Order(**order_info)
    for _attr in order_info.keys():
        assert getattr(order1, _attr) == order_info[_attr]


def test_invalid_side():
    assert OrderSide.is_valid_side("long")
    assert OrderSide.is_valid_side("short")
    assert not OrderSide.is_valid_side("l")
    assert not OrderSide.is_valid_side("s")
    assert not OrderSide.is_valid_side("bad")


def test_invalid_style():
    assert OrderStyle.is_valid_style(MarketOrderStyle(0))
    assert OrderStyle.is_valid_style(LimitOrderStyle(10))

    assert not OrderStyle.is_valid_style(10)


def test_invalid_action():
    assert OrderAction.is_valid_action("open")
    assert OrderAction.is_valid_action("close")

    assert not OrderAction.is_valid_action("o")
    assert not OrderAction.is_valid_action("bad")
