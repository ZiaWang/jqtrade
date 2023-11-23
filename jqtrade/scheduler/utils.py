# -*- coding: utf-8 -*-


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
        task_process = []
        parent_pid = []
        for _p in psutil.process_iter():
            try:
                _cmd_line = " ".join(_p.cmdline())
                if "jqtrade" in _cmd_line and "start_task" in _cmd_line:
                    task_process.append(_p)
                    parent_pid.append(_p.ppid())
            except psutil.AccessDenied:
                if 'python' in _p.name():
                    raise
                else:
                    # windows有一些系统进程，即使有管理员权限，p.cmdline仍会报错，这部分进程忽略
                    # linux没有此问题
                    pass
            except psutil.NoSuchProcess:
                pass

        for _p in task_process:
            if _p.pid in parent_pid:
                continue
            active_tasks.append(_p)
        return active_tasks
    except psutil.AccessDenied:
        print("检测到你没有管理员权限，当前进程需要管理员权限来检查运行中的实盘进程")
        raise


def parse_env(env, sep=";"):
    ret = {}
    envs = env.split(sep)
    for _env in envs:
        _env = _env.strip()
        _k, _v = _env.split("=")
        _k = _k.strip()
        _v = _v.strip()
        ret[_k] = _v
    return ret
