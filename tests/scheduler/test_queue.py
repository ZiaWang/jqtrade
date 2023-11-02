# -*- coding: utf-8 -*-
import random
from concurrent.futures import ThreadPoolExecutor

from quant_engine.scheduler.queue import PriorityQueue, ThreadSafeQueue, QueueEmptyError
from quant_engine.scheduler.event import Event


class TestEvent1(Event):
    pass


class TestEvent2(Event):
    pass


class TestEvent3(Event):
    pass


class TestEvent4(Event):
    pass


class TestEvent5(Event):
    pass


def test_priority_q():
    q = PriorityQueue()

    assert not q._queue
    assert q.empty()

    q.push(TestEvent1(), sort_key=(1, 1))
    q.push(TestEvent2(), sort_key=(1, 2))
    q.push(TestEvent3(), sort_key=(-1, 3))
    q.push(TestEvent4(), sort_key=(2, 1))
    q.push(TestEvent5(), sort_key=(2, -1))

    assert len(q._queue) == 5
    assert not q.empty()

    assert isinstance(q.top(), TestEvent3)
    assert isinstance(q.pop(), TestEvent3)
    assert isinstance(q.pop(), TestEvent1)
    assert isinstance(q.pop(), TestEvent2)
    assert isinstance(q.pop(), TestEvent5)
    assert isinstance(q.pop(), TestEvent4)


def test_thread_safe_q():
    q = ThreadSafeQueue()
    assert q.empty()

    def _handle_q():
        for i in range(10000):
            q.push(1, (random.randint(-10, 10), random.randint(-10, 10)))
            q.top()
            q.empty()

            try:
                q.pop()
            except QueueEmptyError:
                pass

    with ThreadPoolExecutor(10) as pool:
        for _ in range(10):
            pool.submit(_handle_q)
