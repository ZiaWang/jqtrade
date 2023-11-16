# -*- coding: utf-8 -*-
import datetime

from ..scheduler.log import sys_logger

from .order import Order, OrderSide, OrderAction, OrderStatus
from .position import Position
from .config import get_config
from .utils import generate_unique_number


config = get_config()


logger = sys_logger.getChild("account")


class AbsAccount(object):
    def setup(self):
        """ 初始化Account依赖的运行环境

            1. 初始化券商接口（trade_gate）
            2. 注册事件到调度框架，设置定时任务
        """
        raise NotImplementedError

    def sync_balance(self):
        """ 从券商接口同步资金账户资金、持仓数据到本地内存 """
        raise NotImplementedError

    def sync_orders(self):
        """ 从券商接口同步资金账户订单数据到本地内存 """
        raise NotImplementedError

    def order(self, code, amount, style, side):
        """ 转发委托单到券商接口

        Args:
            code: 标的代码
            amount: 委托数量，正数表示开仓，负数表示平仓
            style: 订单类型，支持MarketOrderStyle、LimitOrderStyle实例
            side: 订单方向，支持OrderSide.long、OrderSide.short

        Return:
            order_id: str 内部委托ID
        """
        raise NotImplementedError

    def cancel_order(self, order_id):
        """ 转发撤单到券商接口

        Args:
            order_id: str 内部委托ID
        """
        raise NotImplementedError


class Account(AbsAccount):
    def __init__(self, ctx):
        self._ctx = ctx

        # key: order_id, val: Order object
        self._orders = {}

        # key: code, val: Position object
        self._long_positions = {}
        self._short_positions = {}

        # 总资产
        self._total_assert = 0

        # 可用资金
        self._available_cash = 0

        # 锁定资金
        self._locked_cash = 0

    def setup(self):
        # 初始化券商交易接口
        self._ctx.trade_gate.setup()

        if config.SYNC_BALANCE or config.SYNC_ORDER:
            self._setup_sync_timer()

            self.sync_balance()
            self.sync_orders()

    def _setup_sync_timer(self):
        # 初始化定时任务事件
        from ..scheduler.event_source import EventSource
        from ..scheduler.event import create_event_class, EventPriority
        event_cls = create_event_class("AccountSyncEvent", priority=EventPriority.DEFAULT)
        event_source = EventSource(start=self._ctx.start, end=self._ctx.end)
        now = datetime.datetime.now().replace(microsecond=0)
        if not config.SYNC_PERIOD:
            current = now + datetime.timedelta(seconds=config.SYNC_INTERNAL)
            while current <= now.replace(hour=23, minute=59, second=59):
                event_source.daily(event_cls, current.strftime("%H:%M:%S"))
                current += datetime.timedelta(seconds=config.SYNC_INTERNAL)
        else:
            for _start, _end in config.SYNC_PERIOD:
                _start_dt = datetime.datetime.combine(now.date(), _start)
                _end_dt = datetime.datetime.combine(now.date(), _end)
                current = _start_dt
                while current <= now.replace(hour=23, minute=59, second=59):
                    event_source.daily(event_cls, current.strftime("%H:%M:%S"))
                    current += datetime.timedelta(seconds=config.SYNC_INTERNAL)

        if config.SYNC_BALANCE:
            self._ctx.event_bus.register(event_cls, self.sync_balance)

        if config.SYNC_ORDER:
            self._ctx.event_bus.register(event_cls, self.sync_orders)

        self._ctx.scheduler.schedule(event_source)

    def order(self, code, amount, style, side):
        order_id = generate_unique_number()
        action = OrderAction.close if amount < 0 else OrderAction.open
        order_obj = Order(code=code, price=style.price, amount=abs(amount), action=action,
                          order_id=order_id, style=style, create_time=datetime.datetime.now(),
                          status=OrderStatus.new)
        self._orders[order_id] = order_obj
        try:
            self._ctx.trade_gate.order(order_obj)
        except Exception as e:
            logger.exception("内部下单失败，code=%s, amount=%s, style=%s, side=%s, error=%s" % (
                code, amount, style, side, e
            ))
            order_obj.on_rejected("内部下单失败, error=%s" % e)

    def cancel_order(self, order_id):
        try:
            if order_id not in self._orders:
                logger.error("内部撤单失败，本地找不到内部委托id为%s的委托" % order_id)
                return

            self._ctx.trade_gate.cancel_order(order_id)
        except Exception as e:
            logger.exception("内部撤单异常，order_id=%s, error=%s" % (order_id, e))
            return

    def sync_balance(self, *args, **kwargs):
        try:
            account_info = self._ctx.trade_gate.sync_balance()

            cash_info = account_info.get("cash", {})
            self._total_assert = cash_info.get("total_asset") or self._total_assert
            self._available_cash = cash_info.get("available_cash") or self._available_cash
            self._locked_cash = cash_info.get("locked_cash") or self._locked_cash

            positions = account_info.get("positions", [])
            for _pos_info in positions:
                _side = OrderSide.get_side(_pos_info.pop("side"))
                _pos = Position(
                    code=_pos_info.pop("code"),
                    amount=_pos_info.pop("amount"),
                    available_amount=_pos_info.pop("available_amount"),
                    avg_cost=_pos_info.pop("avg_cost"),
                    side=_side,
                    **_pos_info
                )

                if _pos.side == OrderSide.long:
                    self._long_positions[_pos.code] = _pos
                else:
                    self._short_positions[_pos.code] = _pos
        except Exception as e:
            logger.exception("同步资金和持仓失败，error=%s" % e)

    def sync_orders(self, *args, **kwargs):
        try:
            orders = self._ctx.trade_gate.sync_orders()

            for _order_info in orders:
                _order_id = _order_info["order_id"]
                _local_order = self._orders.get(_order_id)
                _remote_order = Order.load(**_order_info)
                if _local_order is None:
                    logger.error("同步订单时发现本地不存在的订单: %s" % _order_info)
                    self._orders[_order_id] = _remote_order
                    continue

                if _remote_order == _local_order:
                    continue

                self._orders[_order_id] = _remote_order
                self.on_order_updated(_local_order, _remote_order)

        except Exception as e:
            logger.exception("同步订单失败，error=%s" % e)

    def on_order_updated(self, local_order, remote_order):
        self._notify_changed(local_order, remote_order)

    def _notify_changed(self, local_order: Order, remote_order: Order):
        if local_order.status != remote_order.status:
            if remote_order.status == OrderStatus.open:
                self._notify_confirmed(local_order, remote_order)
            elif remote_order.status in (OrderStatus.filling, OrderStatus.filled):
                self._notify_deal(local_order, remote_order)
            elif remote_order.status == OrderStatus.canceling:
                self._notify_canceling(local_order, remote_order)
            elif remote_order.status == OrderStatus.partly_canceled:
                self._notify_canceled(local_order, remote_order)
            elif remote_order.status == OrderStatus.canceled:
                self._notify_canceled(local_order, remote_order)
            elif remote_order.status == OrderStatus.rejected:
                self._notify_rejected(local_order, remote_order)
            else:
                # new, do nothing
                pass
        else:
            if remote_order.status == OrderStatus.filling:
                self._notify_deal(local_order, remote_order)

    @staticmethod
    def _notify_confirmed(local_order, remote_order):
        if local_order.status != OrderStatus.new:
            return
        logger.info("订单已报，id：%s，股票代码：%s，委托数量：%s，委托价格：%s"
                    % (remote_order.order_id, remote_order.code, remote_order.amount, remote_order.price))

    @staticmethod
    def _notify_deal(local_order, remote_order):
        if local_order.has_finished():
            return

        if remote_order.status == OrderStatus.filling:
            logger.info("订单部分成交，id：%s，股票代码：%s，委托数量：%s，委托价格：%s, 已成数量：%s，成交均价：%s，成交金额：%s"
                        % (remote_order.order_id, remote_order.code, remote_order.amount, remote_order.price,
                           remote_order.filled_amount, remote_order.avg_cost, remote_order.deal_balance))
        else:
            logger.info("订单全部成交，id：%s，股票代码：%s，委托数量：%s，委托价格：%s, 已成数量：%s，成交均价：%s，成交金额：%s"
                        % (remote_order.order_id, remote_order.code, remote_order.amount, remote_order.price,
                           remote_order.filled_amount, remote_order.avg_cost, remote_order.deal_balance))

    @staticmethod
    def _notify_canceling(local_order, remote_order):
        if local_order.has_finished():
            return
        logger.info("撤单已报，被撤委托id：%s" % remote_order.order_id)

    @staticmethod
    def _notify_canceled(local_order, remote_order):
        if local_order.has_finished():
            return
        logger.info("订单已撤单，id：%s，股票代码：%s，委托数量：%s，成交数量：%s，撤单数量：%s"
                    % (remote_order.order_id, remote_order.code, remote_order.amount,
                       remote_order.filled_amount, remote_order.canceled_amount))

    @staticmethod
    def _notify_rejected(local_order, remote_order):
        if local_order.has_finished():
            return
        logger.info("订单被废单，id：%s，股票代码：%s，委托数量：%s，委托价格：%s，废单原因：%s"
                    % (remote_order.order_id, remote_order.code, remote_order.amount,
                       remote_order.price, remote_order.err_msg))

    @property
    def orders(self):
        return self._orders

    @property
    def long_positions(self):
        return self._long_positions

    @property
    def short_positions(self):
        return self._short_positions

    @property
    def total_assert(self):
        return self._total_assert

    @property
    def available_cash(self):
        return self._available_cash

    @property
    def locked_cash(self):
        return self._locked_cash
