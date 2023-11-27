# -*- coding: utf-8 -*-
import os
import sys
import importlib

from ..common.log import sys_logger


logger = sys_logger.getChild("loader")


class Loader(object):
    """
    Usage:
        加载用户策略代码代码
    """

    def __init__(self, path):
        self.code_dir, self.code_file = os.path.split(path)

        if self.code_dir == "":
            self.code_dir = "."

    def load(self):
        logger.info(f"加载用户策略代码，code_dir={self.code_dir}，code_file={self.code_file}")
        sys.path.insert(0, self.code_dir)

        module_name = self.code_file.split(".")[0]
        module = importlib.import_module(module_name)
        return module
