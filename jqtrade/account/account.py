# -*- coding: utf-8 -*-
import datetime

from ..common.log import sys_logger
from ..common.utils import generate_unique_number

from .order import Order, OrderSide, OrderAction, OrderStatus
from .position import Position
from .config import get_config


config = get_config()


logger = sys_logger.getChild("account")


class AbsAccount(object):
    def setup(self, options):
        """ 初始化Account依赖的运行环境

            1. 初始化券商接口（trade_gate）
            2. 注册事件到调度框架，设置定时任务
        """
        raise NotImplementedError

    def sync_balance(self, *args, **kwargs):
        """ 从券商接口同步资金账户资金、持仓数据到本地内存 """
        raise NotImplementedError

    def sync_orders(self, *args, **kwargs):
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
    """ 策略账户类

    支持的options：
        "use_account": bool, 策略是否使用account模块，不启用account模块时，仅可用于运行定时任务
        "sync_balance": bool，是否开启同步资金
        "sync_order": bool，是否开启同步订单
        "sync_internal": 浮点数，每次同步的间隔时间，默认5秒
        "sync_period": 同步时间区间，类型为列表，元素为tuple。不设置时，默认启动后一直同步，不管当前是否是交易时间。
            格式参考:
                [
                    (datetime.time(9, 30), datetime.time(11, 30)),
                    (datetime.time(13, 0), datetime.time(15, 0)),
                ]
    """
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

        self.has_synced = False

        self._options = None

    def setup(self, options):
        logger.info("setup account")

        self._options = options

        # 初始化券商交易接口
        self._ctx.trade_gate.setup(options)

        # 初始化account相关事件循环配置，并触发一次资金、持仓、订单同步
        if self.need_sync_balance or self.need_sync_order:
            self._setup_sync_timer()

            # setup触发一次同步
            self.sync_balance()
            self.sync_orders()

    @property
    def need_sync_balance(self):
        return bool(self._options.get("sync_balance", config.SYNC_BALANCE))

    @property
    def need_sync_order(self):
        return bool(self._options.get("sync_balance", config.SYNC_BALANCE))

    def _setup_sync_timer(self):
        logger.info("setup account sync timer")
        # 初始化定时任务事件
        from ..scheduler.event_source import EventSource
        from ..scheduler.event import create_event_class, EventPriority
        event_cls = create_event_class("AccountSyncEvent", priority=EventPriority.DEFAULT)
        event_source = EventSource(start=self._ctx.start, end=self._ctx.end)
        now = datetime.datetime.now().replace(microsecond=0)

        sync_internal = bool(self._options.get("sync_internal", config.SYNC_INTERNAL))
        sync_period = self._options.get("sync_period", config.SYNC_PERIOD)
        if not sync_period:
            current = now + datetime.timedelta(seconds=sync_internal)
            while current <= now.replace(hour=23, minute=59, second=59):
                event_source.daily(event_cls, current.strftime("%H:%M:%S"))
                current += datetime.timedelta(seconds=sync_internal)
        else:
            for _period in sync_period:
                if len(_period) != 2:
                    raise ValueError(f"sync period设置错误：{_period}")
                _start, _end = _period
                if not (isinstance(_start, datetime.time) and isinstance(_end, datetime.time)):
                    raise ValueError(f"sync period设置的时间类型错误，需要是datetime.time类型。")
                _start_dt = datetime.datetime.combine(now.date(), _start)
                _end_dt = datetime.datetime.combine(now.date(), _end)
                current = _start_dt
                while current <= now.replace(hour=23, minute=59, second=59):
                    event_source.daily(event_cls, current.strftime("%H:%M:%S"))
                    current += datetime.timedelta(seconds=sync_internal)

        if self.need_sync_balance:
            self._ctx.event_bus.register(event_cls, self.sync_balance)

        if self.need_sync_order:
            self._ctx.event_bus.register(event_cls, self.sync_orders)

        self._ctx.scheduler.schedule(event_source)

    def order(self, code, amount, style, side):
        order_id = str(generate_unique_number())
        action = OrderAction.close if amount < 0 else OrderAction.open
        order_obj = Order(code=code, price=style.price, amount=abs(amount), action=action,
                          order_id=order_id, style=style, create_time=datetime.datetime.now(),
                          status=OrderStatus.new)
        self._orders[order_id] = order_obj
        try:
            logger.info(f"提交订单，订单id：{order_id}，code：{code}，price：{style.price}，amount：{amount}，"
                        f"action：{action}，style：{style}")
            self._ctx.trade_gate.order(order_obj)
            return order_id
        except Exception as e:
            logger.exception(f"内部下单异常，code={code}, amount={amount}, style={style}, side={side}, error={e}")

    def cancel_order(self, order_id):
        try:
            if order_id not in self._orders:
                logger.error(f"发起撤单失败，本地找不到内部委托id为{order_id}的委托")
                return

            logger.info("提交撤单，被撤订单id：%s" % order_id)
            self._ctx.trade_gate.cancel_order(order_id)
        except Exception as e:
            logger.exception(f"内部撤单异常，order_id={order_id}, error={e}")
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
            logger.exception(f"同步资金和持仓失败，error={e}")

    def sync_orders(self, *args, **kwargs):
        try:
            orders = self._ctx.trade_gate.sync_orders()

            for _order_info in orders:
                _order_id = str(_order_info["order_id"])
                _local_order = self._orders.get(_order_id)
                _remote_order = Order.load(**_order_info)
                if _local_order is None:
                    if self.has_synced:
                        logger.error(f"从trade_gate加载到本地不存在的订单: {_order_info}")
                    else:
                        logger.error(f"从trade_gate加载订单: {_order_info}")
                    self._orders[_order_id] = _remote_order
                    continue

                if _remote_order == _local_order:
                    continue
                else:
                    self._orders[_order_id] = _remote_order
                    self.on_order_updated(_local_order, _remote_order)

            self.has_synced = True
        except Exception as e:
            logger.exception(f"同步订单失败，error={e}")

    def on_order_updated(self, local_order, remote_order):
        self._notify_changed(local_order, remote_order)

    def _notify_changed(self, local_order, remote_order):
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
        logger.info(f"订单已报，id：{remote_order.order_id}，股票代码：{remote_order.code}，"
                    f"委托数量：{remote_order.amount}，委托价格：{remote_order.price}")

    @staticmethod
    def _notify_deal(local_order, remote_order):
        if local_order.has_finished():
            return

        if remote_order.status == OrderStatus.filling:
            logger.info(f"订单部分成交，id：{remote_order.order_id}，股票代码：{remote_order.code}，"
                        f"委托数量：{remote_order.amount}，委托价格：{remote_order.price}, "
                        f"已成数量：{remote_order.filled_amount}，成交均价：{remote_order.avg_cost}，"
                        f"成交金额：{remote_order.deal_balance}")
        else:
            logger.info(f"订单全部成交，id：{remote_order.order_id}，股票代码：{remote_order.code}，"
                        f"委托数量：{remote_order.amount}，委托价格：{remote_order.price}, "
                        f"已成数量：{remote_order.filled_amount}，成交均价：{remote_order.avg_cost}，"
                        f"成交金额：{remote_order.deal_balance}")

    @staticmethod
    def _notify_canceling(local_order, remote_order):
        if local_order.has_finished():
            return
        logger.info(f"撤单已报，被撤委托id：{remote_order.order_id}")

    @staticmethod
    def _notify_canceled(local_order, remote_order):
        if local_order.has_finished():
            return
        logger.info(f"订单已撤单，id：{remote_order.order_id}，股票代码：{remote_order.code}，"
                    f"委托数量：{remote_order.amount}，成交数量：{remote_order.filled_amount}，"
                    f"撤单数量：{remote_order.canceled_amount}")

    @staticmethod
    def _notify_rejected(local_order, remote_order):
        if local_order.has_finished():
            return
        logger.info(f"订单被废单，id：{remote_order.order_id}，股票代码：{remote_order.code}，"
                    f"委托数量：{remote_order.amount}，委托价格：{remote_order.price}，废单原因：{remote_order.err_msg}")

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
