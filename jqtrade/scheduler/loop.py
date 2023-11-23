# -*- coding: utf-8 -*-
import time
import pyuv
import signal
import traceback

from ..common.log import sys_logger
from ..common.utils import milliseconds_to_dt

from .queue import ThreadSafeQueue, QueueEmptyError
from .message import Message


logger = sys_logger.getChild("loop")


class EventLoop(object):
    """ 事件循环类

        1. 管理事件循环
        2. 取出事件并触发事件回调
        3. 监听外部信号
    """

    def __init__(self):
        self._queue = ThreadSafeQueue()

        self._uvloop = pyuv.Loop()
        self._loop_notifier = pyuv.Async(self._uvloop, self.check_queue)
        self._timer = pyuv.Timer(self._uvloop)

        self._stop_requested = False
        self._exception = None

        self._exit_checkers = []
        self._signal_handlers = {}

        self._strategy_time = None

    def setup(self):
        # stop_task
        self.register_signal_callback(signal.SIGTERM, self.handle_signal)

        # ctrl c
        self.register_signal_callback(signal.SIGINT, self.handle_signal)

    def run(self):
        logger.info("loop run")

        self.setup()
        self._uvloop.run()

        if self._exception:
            raise self._exception

    def stop(self):
        logger.info("stop loop")
        if not self._stop_requested:
            self._stop_requested = True
            self._notify_loop()

    def check_queue(self, *args, **kwargs):
        logger.debug("check_queue run")
        while not self._stop_requested:
            try:
                message = self._queue.pop()
                logger.debug("check_queue. pop message: %s" % message)
            except QueueEmptyError:
                logger.info("loop queue empty. exit")
                self._stop_requested = True
                break

            now = self.get_current_time()
            if message.time > now:
                if self.check_exit(message.time):
                    self.stop()
                    break

                wait_time = (message.time - now) / 1000.0
                logger.debug("start timer, wait %s seconds", wait_time)
                self._timer.stop()
                self._uvloop.update_time()
                self._timer.start(
                    self.check_queue,
                    timeout=wait_time,
                    repeat=0)

                logger.debug("check_queue. push message: %s" % message)
                self.push_message(message, notify=False)
                break
            else:
                self.handle_message(message)

        if self._stop_requested:
            self._uvloop.stop()

    def handle_message(self, message):
        try:
            logger.debug("handle message: %s" % message)
            self._strategy_time = message.time
            message.callback(**message.callback_data)
        except Exception as e:
            logger.exception("handle message failed. message=%s, error=%s" % (message, e))
            e.tb = traceback.format_exc()
            self._exception = e
            self.stop()

    def _notify_loop(self):
        self._loop_notifier.send()

    def push_message(self, message, notify=True):
        self._queue.push(message, message.sort_key)

        if notify:
            self._notify_loop()

    @staticmethod
    def get_current_time():
        return int(time.time() * 1000)

    def register_exit_checker(self, callback):
        logger.debug("register_exit_checker. callback: %s" % callback)
        self._exit_checkers.append(callback)

    def check_exit(self, ts):
        logger.debug("check_exit ts: %s" % ts)
        for checker in self._exit_checkers:
            if checker(self.get_current_time(), ts):
                logger.info("check_exit. exit now")
                return True
        return False

    def defer(self, delay, callback, *args, **kws):
        logger.debug("defer callback: %s, delay: %s" % (callback, delay))
        self.push_message(Message(time=self.get_current_time() + int(delay), callback=lambda: callback(*args, **kws)))

    def register_signal_callback(self, signum, callback):
        signal_handler = self._signal_handlers.get(signum, None)
        if signal_handler is None:
            signal_handler = self._signal_handlers[signum] = pyuv.Signal(self._uvloop)
        signal_handler.stop()
        signal_handler.start(lambda handle, sig: callback(sig), signum)

    def handle_signal(self, sig):
        logger.info("handle signal: %s" % sig)
        self.stop()

    @property
    def current_dt(self):
        return milliseconds_to_dt(self.get_current_time())

    @property
    def strategy_dt(self):
        if self._strategy_time:
            return milliseconds_to_dt(self._strategy_time)
        return None
