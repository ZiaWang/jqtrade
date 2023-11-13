# -*- coding: utf-8 -*-
import time

from jqtrade.account.utils import OrderIDProducer


def test_order_id_producer():
    producer = OrderIDProducer()

    ret = []
    for i in range(3):
        for _ in range(100):
            ret.append(producer.create_id())
        time.sleep(1)

    assert len(set(ret)) == 300
    assert isinstance(ret[0], str)
