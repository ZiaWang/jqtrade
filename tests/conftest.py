# -*- coding: utf-8 -*-
import os
import sys


def setup():
    this_dir = os.path.abspath(os.path.dirname(__file__))
    project_dir = os.path.abspath(os.path.join(this_dir, ".."))
    sys.path.append(project_dir)

    from jqtrade.common.log import setup_logger
    setup_logger("DEBUG")


setup()
