# -*- coding: utf-8 -*-


class Message(object):
    """
    Usage:
        封装事件的消息类，事件队列中的实际对象
    """

    _unique_num = 0

    def __init__(self, time, callback, callback_data=None, priority=0):
        self.time = int(time)
        self.callback = callback
        self.callback_data = callback_data or {}
        self.priority = priority

        Message._unique_num += 1
        self.seq_number = Message._unique_num

    @property
    def sort_key(self):
        return self.time, -self.priority, self.seq_number

    def __repr__(self):
        return f"Message(time={self.time}, callback={self.callback.__name__}, " \
               f"priority={self.priority}, seq_number={self.seq_number})"
