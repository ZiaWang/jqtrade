# -*- coding: utf-8 -*-

import heapq
import threading


class QueueEmptyError(Exception):
    pass


class PriorityQueue(object):
    """ 非线程安全的优先队列 """

    def __init__(self):
        self._queue = []

    def push(self, item, sort_key):
        heapq.heappush(self._queue, (sort_key, item))

    def pop(self):
        try:
            return heapq.heappop(self._queue)[1]
        except IndexError:
            raise QueueEmptyError()

    def top(self):
        try:
            return self._queue[0][1]
        except IndexError:
            raise QueueEmptyError()

    def empty(self):
        return len(self._queue) == 0


class ThreadSafeQueue(PriorityQueue):
    """ 线程安全的优先队列 """

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
