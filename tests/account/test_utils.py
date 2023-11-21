# -*- coding: utf-8 -*-
import time
import pytest

from jqtrade.account.utils import generate_unique_number, simple_retry


def test_order_id_producer():
    ret = []
    for i in range(3):
        for _ in range(100):
            ret.append(generate_unique_number())
        time.sleep(1)

    assert len(set(ret)) == 300
    assert isinstance(ret[0], int)


def test_simple_retry():
    retry_count = [0]
    def func():
        print("run func")
        retry_count[0] += 1
        raise ValueError("test")
    func1 = simple_retry()(func)
    with pytest.raises(ValueError):
        func1()
    assert retry_count[0] == 4

    retry_count = [0]
    func2 = simple_retry(on_exception=lambda e: isinstance(e, TypeError))(func)

    with pytest.raises(ValueError):
        func2()

    assert retry_count[0] == 1

    retry_count = [0]
    func2 = simple_retry(on_exception=lambda e: isinstance(e, ValueError))(func)
    with pytest.raises(ValueError):
        func2()
    assert retry_count[0] == 4
