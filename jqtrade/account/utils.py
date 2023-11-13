# -*- coding: utf-8 -*-
import os
import time
import datetime


class OrderIDProducer(object):
    def __init__(self):
        self._prefix = None
        self._ts = None
        self._count = 0

    def create_id(self):
        if self._ts is None:
            self.refresh()

        ts = int(time.time())
        if ts != self._ts:
            self.refresh()

        self._count += 1
        return "%s-%s" % (self._prefix, self._count)

    def refresh(self):
        self._prefix = str(os.getpid()) + "-" + datetime.datetime.now().strftime("%m%d%H%M%S")
        self._ts = int(time.time())
        self._count = 0
