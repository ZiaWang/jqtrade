# -*- coding: utf-8 -*-
import argparse


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-V", "--version", action="store_true", help="获取版本信息")

    sub_parsers = parser.add_subparsers()

    # 启动实盘任务
    start_task_parser = sub_parsers.add_parser("start_task", help="创建新的实盘任务")
    start_task_parser.add_argument("-n", "--name", required=True, help="实盘任务名称，唯一标识该实盘任务，不能重复")
    start_task_parser.add_argument("-c", "--code", required=True, help="策略代码路径")
    start_task_parser.add_argument("-o", "--out", required=False, default=None, help="日志路径，不指定时打印到标准输出/错误")
    start_task_parser.add_argument("-e", "--env", required=False, default=None,
                                   help="指定实盘策略进程运行环境变量，多个环境变量使用分号分隔。"
                                        "示例: -e PATH=./bin:/usr/bin;PYTHONPATH=./package;USER=test")
    start_task_parser.add_argument("--config", required=False, default=None, help="指定自定义配置文件路径")
    start_task_parser.add_argument("--debug", action="store_true", help="是否开启debug模式，debug模式日志更丰富些")
    start_task_parser.set_defaults(func=start_task)

    # 查询运行中的实盘任务
    get_tasks_parser = sub_parsers.add_parser("get_tasks", help="查询当前运行中的实盘任务")
    get_tasks_parser.set_defaults(func=get_tasks)

    # 停止实盘任务
    stop_task_parser = sub_parsers.add_parser("stop_task", help="停止运行中的实盘任务")
    stop_task_parser.add_argument("-n", "--name", default=None, help="通过指定实盘名称来停止实盘")
    stop_task_parser.add_argument("-p", "--pid", type=int, default=None, help="通过指定实盘进程pid来停止实盘")
    stop_task_parser.add_argument("--all", action="store_true", help="停止所有运行中的实盘任务")
    stop_task_parser.add_argument("-f", "--force", action="store_true", help="是否强制杀掉策略进程，"
                                                                             "不指定时，会等待策略进程处理完当前事务再退出")
    stop_task_parser.set_defaults(func=stop_task)

    options = parser.parse_args()

    if options.version:
        import jqtrade
        print(jqtrade.__version__)
    else:
        options.func(options)


def start_task(options):
    """
    python -m quant_engine start_task -c tests/scheduler/strategy_demo.py --debug -n demo
    """
    from .scheduler.runner import TaskRunner
    runner = TaskRunner(options.code, options.out, options.name, options.env, options.debug, options.config)
    runner.run()


def get_tasks(options):
    """
    python -m quant_engine get_tasks
    """
    from .scheduler.utils import get_activate_task_process, parse_task_info

    active_tasks = get_activate_task_process()
    if not active_tasks:
        print("当前没有运行中的实盘任务进程")
        return

    print("当前活跃的实盘任务进程".center(30, "-"))
    for _p in active_tasks:
        _cmd = _p.cmdline()
        _task_info = parse_task_info(_cmd)
        _task_info["pid"] = _p.pid
        _task_info["cmd"] = _cmd
        print("名称: {name}\n"
              "pid: {pid}\n"
              "代码路径: {code}\n"
              "日志路径: {out}\n"
              "自定义环境变量: {env}\n"
              "是否debug模式: {debug}\n"
              "cmd: {cmd}\n\n".format(**_task_info))


def stop_task(options):
    """
    python -m quant_engine stop_task -n demo1
    python -m quant_engine stop_task -p 12345
    python -m quant_engine stop_task --all
    """
    from .scheduler.utils import get_activate_task_process, parse_task_info

    active_tasks = get_activate_task_process()

    if not options.name and not options.pid and not options.all:
        raise ValueError("--name/--pid/--all至少指定一项")

    killed_pid = []

    def _kill(_p, force=False):
        if force:
            _p.kill()
            print(f"强制停止进程 {_p.pid}")
        else:
            import signal
            _p.send_signal(signal.SIGTERM)
            print(f"尝试停止进程 {_p.pid}，已向该进程发送SIGTERM停止信号")
        killed_pid.append(_p.pid)

    if options.all:
        for _p in active_tasks:
            _kill(_p, options.force)
    elif options.pid:
        for _p in active_tasks:
            if _p.pid == options.pid:
                _kill(_p, options.force)
                break
    else:
        for _p in active_tasks:
            _task_info = parse_task_info(_p.cmdline())
            if options.name == _task_info["name"]:
                _kill(_p, options.force)

    if not killed_pid:
        print("未找到需要停止的进程")
    elif killed_pid and not options.force:
        print("若您执行完stop_task命令后发现策略进程仍在运行，请尝试使用 -f 或 --force 选项强制停止进程")


if __name__ == '__main__':
    main()
