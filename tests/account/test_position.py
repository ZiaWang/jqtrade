# -*- coding: utf-8 -*-

from jqtrade.account.position import Position
from jqtrade.account.order import OrderSide


def test_pos_instance():

    pos_info1 = {
        "code": "000001.XSHE",
        "amount": 1000,
        "available_amount": 600,
        "avg_cost": 11.11,
        "side": OrderSide.long,
    }
    pos1 = Position(**pos_info1)
    assert pos1.code == "000001.XSHE"
    assert pos1.amount == 1000
    assert pos1.available_amount == 600
    assert pos1.locked_amount == 400
    assert pos1.side == OrderSide.long
    assert pos1.position_value is None
    assert pos1.last_price is None
    assert pos1.avg_cost == 11.11

    pos_info1 = {
        "code": "000002.XSHE",
        "amount": 2000,
        "available_amount": 600,
        "avg_cost": 11.12,
        "side": OrderSide.short,
        "position_value": 24000,
        "last_price": 12
    }
    pos1 = Position(**pos_info1)
    assert pos1.code == "000002.XSHE"
    assert pos1.amount == 2000
    assert pos1.available_amount == 600
    assert pos1.locked_amount == 1400
    assert pos1.side == OrderSide.short
    assert pos1.position_value == 24000
    assert pos1.last_price == 12
    assert pos1.avg_cost == 11.12
