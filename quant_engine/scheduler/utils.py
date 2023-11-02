# -*- coding: utf-8 -*-

import datetime


def dt_to_milliseconds(dt):
    return int(dt.timestamp() * 1000 + dt.microsecond / 1000)


def milliseconds_to_dt(milliseconds):
    return datetime.datetime.fromtimestamp(milliseconds / 1000.)


def parse_task_info(cmd_line):
    info = {"debug": False, "env": None, "out": None}
    for _idx, _item in enumerate(cmd_line):
        if _item in ("-c", "--code"):
            info["code"] = cmd_line[_idx+1]
        elif _item in ("-o", "--out"):
            info["out"] = cmd_line[_idx + 1]
        elif _item in ("-n", "--name"):
            info["name"] = cmd_line[_idx + 1]
        elif _item in ("-e", "--env"):
            info["env"] = cmd_line[_idx + 1]
        elif _item == "--debug":
            info["debug"] = True
    return info


def get_activate_task_process():
    active_tasks = []

    import psutil
    try:
        for _p in psutil.process_iter():
            _cmd_lines = _p.cmdline()
            if "quant_engine" in _cmd_lines and "start_task" in _cmd_lines:
                active_tasks.append(_p)
        return active_tasks
    except psutil.AccessDenied:
        print("检测到你没有管理员权限，当前进程需要管理员权限来检查运行中的实盘进程")
        raise
