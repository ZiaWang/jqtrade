# -*- coding: utf-8 -*-
import re
import datetime

from ..common.exceptions import InvalidParam
from ..common.log import sys_logger
from ..common.utils import dt_to_milliseconds

from .message import Message
from .context import Context
from .config import get_config


config = get_config()


logger = sys_logger.getChild("event_source")


class EventSource(object):
    """ 事件源类，用于根据用户设置的定时任务生成对应事件 """

    def __init__(self, start=None, end=None):
        """
        Args:
            start: 生成事件的起始时间，默认从当前时间点开始
            end: 生成事件的结束时间，不会生成 '时间>end' 的事件
        """
        self._daily = []
        self._events = []
        self._days = []

        self._start = start
        self._end = end

        self._need_regenerate_events = True

        self._event_changed_callback = []

    def setup(self):
        if self._start is None or not config.ENABLE_HISTORY_START:
            self._start = datetime.datetime.now()

        self._reset_events_if_needed()

    def _reset_events_if_needed(self):
        if not self._need_regenerate_events:
            return

        self._events = []
        self._days = self._get_days()
        self._need_regenerate_events = False

    def _get_days(self, count=config.EVENT_DAYS_COUNT):
        start = self._start.date()
        days = []
        for _delta in range(count):
            days.append(start + datetime.timedelta(days=_delta))
        return days

    def daily(self, event_cls, time_expr):
        self._daily.append((time_expr, event_cls))
        self.on_events_changed()

    def on_events_changed(self):
        self._need_regenerate_events = True

        for _callback in self._event_changed_callback:
            _callback(self)

    def register_event_changed(self, callback):
        self._event_changed_callback.append(callback)

    def peek_next_event(self):
        self.gen_events()
        if len(self._events) == 0:
            return
        return self._events[0]

    def get_next_event(self):
        self.gen_events()
        if len(self._events) == 0:
            return
        return self._events.pop(0)

    def gen_events(self):
        self._reset_events_if_needed()
        if len(self._events):
            return

        if len(self._events) == 0:
            if len(self._days) == 0:
                self._days = self._get_days()

            day = self._days.pop(0)
            self.add_daily_events(day)
        self._events.sort(key=lambda e: e[0])

    def add_daily_events(self, day):
        for _time_expr, _event_cls in self._daily:
            self.add_event(day, _time_expr, _event_cls)

    def add_event(self, day, time_expr, event_cls):
        if ':' in time_expr:
            time_info = time_expr.split(':')
            hour, minute = time_info[:2]
            try:
                second = time_info[2]
            except IndexError:
                second = 0

            hour = int(hour)
            minute = int(minute)
            second = int(second)
            dt = datetime.datetime.combine(day, datetime.time(hour, minute, second))
        else:
            dt = self.expr_to_time(day, time_expr)

        if dt < self._start:
            return

        if self._end and dt > self._end:
            return

        self._events.append((dt, event_cls()))

    @staticmethod
    def expr_to_time(day, time_expr):
        bases = {
            'open': datetime.datetime.combine(day, config.MARKET_OPEN_TIME),
            'close': datetime.datetime.combine(day, config.MARKET_CLOSE_TIME),
        }
        base, op, offset = TimeExprParser.parse(time_expr)

        dt = bases[base]
        if op == '+':
            dt += offset
        else:
            dt -= offset
        return dt


class EventSourceScheduler(object):
    """ 事件源调度器，一个策略可能会有多个事件源。此调度器用于管理事件源，通过事件源生成事件并推送到队列中 """

    _unique_id = 0

    def __init__(self):
        self._event_sources = {}

    def schedule(self, event_source):
        self.__class__._unique_id += 1
        schedule_id = self.__class__._unique_id
        logger.debug("schedule event_source: %s, schedule_id: %s" % (event_source, schedule_id))
        self._event_sources[schedule_id] = event_source

        ctx = Context.get_instance()

        def reschedule(es):
            logger.debug("reschedule event_source: %s" % es)
            self.unschedule(schedule_id)
            self.schedule(es)

        def callback():
            if schedule_id not in self._event_sources:
                logger.debug("schedule schedule_id(%s) not found" % schedule_id)
                return
            dt_evt = event_source.get_next_event()
            if not dt_evt:
                logger.debug("schedule event not found")
                return
            dt, evt = dt_evt
            logger.debug("schedule emit event: %s, dt: %s" % (evt, dt))
            ctx.event_bus.emit(evt)
            push_next_msg()

        def push_next_msg():
            dt_evt = event_source.peek_next_event()
            if not dt_evt:
                return
            dt, evt = dt_evt
            logger.debug("schedule push event: %s, dt: %s" % (evt, dt))
            ctx.loop.push_message(Message(
                time=dt_to_milliseconds(dt),
                callback=callback,
                priority=evt.priority))

        event_source.register_event_changed(reschedule)
        push_next_msg()
        return schedule_id

    def unschedule(self, schedule_id):
        logger.debug("unschedule event_source. schedule_id: %s" % schedule_id)
        self._event_sources.pop(schedule_id, None)


class TimeExprParser(object):
    """ 解析run_daily中的time字段 """

    ALLOWED_BASE = ('open', 'close')

    @staticmethod
    def _parse_offset(offset):
        m = re.match(r'^(([0-9]{1,2}[hms]){1,3})$', offset)
        if m is None:
            raise InvalidParam('invalid time offset %s' % offset)
        ret = re.findall(r'([0-9]{1,2})([hms])', offset)
        ret = dict((v, int(k)) for k, v in ret)
        return datetime.timedelta(hours=ret.get('h', 0), minutes=ret.get('m', 0), seconds=ret.get('s', 0))

    @classmethod
    def parse(cls, expr):
        ret = re.split(r'([+-])', expr)
        if len(ret) == 1:
            base = ret[0]
            if base not in cls.ALLOWED_BASE:
                raise InvalidParam('invalid time base %s, time base must be one of %s' % (base, cls.ALLOWED_BASE))
            return base, '+', datetime.timedelta()
        elif len(ret) != 3:
            raise InvalidParam('invalid time expr %s' % expr)
        else:
            base, op, offset = ret
            return base, op, cls._parse_offset(offset)
