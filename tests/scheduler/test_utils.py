# -*- coding: utf-8 -*-
import datetime

from jqtrade.scheduler.utils import dt_to_milliseconds, parse_task_info, get_activate_task_process


def test_dt_to_milliseconds():
    assert dt_to_milliseconds(datetime.datetime(2023, 10, 30)) == 1698595200000


def test_parse_task_info():
    assert parse_task_info(['sudo', '-E',
                            'python', '-m', 'jqtrade', 'start_task',
                            '-c', 'tests/scheduler/strategies/strategy_demo.py',
                            '-n', 'demo',
                            '--debug',
                            '-o', 'demo.log',
                            '-e', 'AAAA=1;BBB=2']) == {
        "debug": True,
        "code": "tests/scheduler/strategies/strategy_demo.py",
        "name": "demo",
        "out": "demo.log",
        "env": "AAAA=1;BBB=2",
    }

    assert parse_task_info(['python', '-m', 'jqtrade', 'start_task',
                            '-c', 'tests/scheduler/strategies/strategy_demo.py',
                            '-n', 'demo']) == {
               "debug": False,
               "code": "tests/scheduler/strategies/strategy_demo.py",
               "name": "demo",
               "out": None,
               "env": None,
           }

    assert parse_task_info(['python', '-m', 'jqtrade', 'start_task',
                            '-c', 'tests/scheduler/strategies/strategy_demo.py',
                            '-n', 'demo',
                            '--debug',
                            '-o', 'demo.log',
                            '-e', 'AAAA=1;BBB=2']) == {
        "debug": True,
        "code": "tests/scheduler/strategies/strategy_demo.py",
        "name": "demo",
        "out": "demo.log",
        "env": "AAAA=1;BBB=2",
    }
