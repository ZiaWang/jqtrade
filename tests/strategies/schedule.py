# -#- coding: utf-8 -*-
import datetime

__options__ = {
    "start": "2023-10-01",
    "end": "2023-11-01",
    "debug": True
}


g = {
    "func_0800": 0,
    "func_0900": 0,

    "func_open_sub_1h": 0,
    "func_open_sub_30m": 0,
    "func_open_sub_30s": 0,
    "func_open": 0,
    "func_open_add_30s": 0,
    "func_open_add_30m": 0,
    "func_open_add_1h": 0,

    "func_1100": 0,
    "func_1200": 0,
    "func_1300": 0,
    "func_1400": 0,
    "func_1500": 0,

    "func_close_sub_1h": 0,
    "func_close_sub_30m": 0,
    "func_close_sub_30s": 0,
    "func_close": 0,
    "func_close_add_30s": 0,
    "func_close_add_30m": 0,
    "func_close_add_1h": 0,

    "func_every_minute": 0,
}


def process_initialize(context):
    log.info("process_initialize run")
    run_daily(func_0800, "08:00:00")
    run_daily(func_0900, "09:00:00")

    run_daily(func_open_sub_1h, "open-1h")
    run_daily(func_open_sub_30m, "open-30m")
    run_daily(func_open_sub_30s, "open-30s")
    run_daily(func_open, "open")
    run_daily(func_open_add_30s, "open+30s")
    run_daily(func_open_add_30m, "open+30m")
    run_daily(func_open_add_1h, "open+1h")

    run_daily(func_1100, "11:00:00")
    run_daily(func_1200, "12:00:00")
    run_daily(func_1300, "13:00:00")
    run_daily(func_1400, "14:00:00")
    run_daily(func_1500, "15:00:00")

    run_daily(func_close_sub_1h, "close-1h")
    run_daily(func_close_sub_30m, "close-30m")
    run_daily(func_close_sub_30s, "close-30s")
    run_daily(func_close, "close")
    run_daily(func_close_add_30s, "close+30s")
    run_daily(func_close_add_30m, "close+30m")
    run_daily(func_close_add_1h, "close+1h")

    run_daily(func_every_minute, "every_minute")


def func_0800(context):
    print(context)
    g["func_0800"] += 1
    assert context.strategy_dt.time() == datetime.time(8, 0)


def func_0900(context):
    g["func_0900"] += 1
    assert context.strategy_dt.time() == datetime.time(9, 0)


def func_open_sub_1h(context):
    g["func_open_sub_1h"] += 1
    assert context.strategy_dt.time() == datetime.time(8, 30)


def func_open_sub_30m(context):
    g["func_open_sub_30m"] += 1
    assert context.strategy_dt.time() == datetime.time(9, 0)


def func_open_sub_30s(context):
    g["func_open_sub_30s"] += 1
    assert context.strategy_dt.time() == datetime.time(9, 29, 30)


def func_open(context):
    g["func_open"] += 1
    assert context.strategy_dt.time() == datetime.time(9, 30)


def func_open_add_30s(context):
    g["func_open_add_30s"] += 1
    assert context.strategy_dt.time() == datetime.time(9, 30, 30)


def func_open_add_30m(context):
    g["func_open_add_30m"] += 1
    assert context.strategy_dt.time() == datetime.time(10, 0, 0)


def func_open_add_1h(context):
    g["func_open_add_1h"] += 1
    assert context.strategy_dt.time() == datetime.time(10, 30, 0)


def func_1100(context):
    g["func_1100"] += 1
    assert context.strategy_dt.time() == datetime.time(11, 0)


def func_1200(context):
    g["func_1200"] += 1
    assert context.strategy_dt.time() == datetime.time(12, 0)


def func_1300(context):
    g["func_1300"] += 1
    assert context.strategy_dt.time() == datetime.time(13, 0)


def func_1400(context):
    g["func_1400"] += 1
    assert context.strategy_dt.time() == datetime.time(14, 0)


def func_1500(context):
    g["func_1500"] += 1
    assert context.strategy_dt.time() == datetime.time(15, 0)


def func_close_sub_1h(context):
    g["func_close_sub_1h"] += 1
    assert context.strategy_dt.time() == datetime.time(14, 0)


def func_close_sub_30m(context):
    g["func_close_sub_30m"] += 1
    assert context.strategy_dt.time() == datetime.time(14, 30)


def func_close_sub_30s(context):
    g["func_close_sub_30s"] += 1
    assert context.strategy_dt.time() == datetime.time(14, 59, 30)


def func_close(context):
    g["func_close"] += 1
    assert context.strategy_dt.time() == datetime.time(15, 0)


def func_close_add_30s(context):
    g["func_close_add_30s"] += 1
    assert context.strategy_dt.time() == datetime.time(15, 0, 30)


def func_close_add_30m(context):
    g["func_close_add_30m"] += 1
    assert context.strategy_dt.time() == datetime.time(15, 30)


def func_close_add_1h(context):
    g["func_close_add_1h"] += 1
    assert context.strategy_dt.time() == datetime.time(16, 0)


def func_every_minute(context):
    g["func_every_minute"] += 1


def process_exit(context):
    for _k, _v in g.items():
        print("%s %s" % (_k, _v))
        if _k == "func_every_minute":
            assert _v == 242 * 31   # 09:30:00、13:00:00
        else:
            assert _v == 31
