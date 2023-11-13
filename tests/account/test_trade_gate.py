# -*- coding: utf-8 -*-
import pytest

from jqtrade.account.trade_gate import AttrDict, InternalError


def test_attr_dict():
    d = AttrDict(a=1, b=2, c=3)
    assert d.a == d["a"] == 1
    assert d.b == d["b"] == 2
    assert d.c == d["c"] == 3

    class Req(AttrDict):
        _required_keys = ("a", "b")

    with pytest.raises(InternalError):
        Req()

    with pytest.raises(InternalError):
        Req(a=1)

    with pytest.raises(InternalError):
        Req(b=2)

    req = Req(a=1, b=2, c=3)
    assert req.a == req["a"] == 1
    assert req.b == req["b"] == 2
    assert req.c == req["c"] == 3

    with pytest.raises(KeyError):
        req["d"]

    with pytest.raises(AttributeError):
        req.d
