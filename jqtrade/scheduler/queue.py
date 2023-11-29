# -*- coding: utf-8 -*-
from ..common.log import sys_logger

import heapq
import threading


logger = sys_logger.getChild("queue")


class QueueEmptyError(Exception):
    pass


class PriorityQueue(object):
    """
    Usage:
        非线程安全的优先队列
    """

    def __init__(self):
        self._queue = []

    def push(self, item, sort_key):
        logger.debug(f"push queue. item={item}, sort_key={sort_key}")
        heapq.heappush(self._queue, (sort_key, item))

    def pop(self):
        try:
            sort_key, msg = heapq.heappop(self._queue)
            logger.debug(f"pop queue. msg={msg}, sort_key={sort_key}")
            return msg
        except IndexError:
            raise QueueEmptyError()

    def top(self):
        try:
            sort_key, msg = self._queue[0]
            logger.debug(f"pop queue. item={msg}, sort_key={sort_key}")
            return msg
        except IndexError:
            raise QueueEmptyError()

    def empty(self):
        return len(self._queue) == 0


class ThreadSafeQueue(PriorityQueue):
    """
    Usage:
        线程安全的优先队列
    """

    def __init__(self):
        super(ThreadSafeQueue, self).__init__()

        self._lock = threading.Lock()

    def push(self, *args, **kwargs):
        with self._lock:
            return super(ThreadSafeQueue, self).push(*args, **kwargs)

    def pop(self):
        with self._lock:
            return super(ThreadSafeQueue, self).pop()

    def top(self):
        with self._lock:
            return super(ThreadSafeQueue, self).top()

    def empty(self):
        with self._lock:
            return super(ThreadSafeQueue, self).empty()
