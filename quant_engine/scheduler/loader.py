# -*- coding: utf-8 -*-
import os
import sys
import importlib


class Loader(object):
    """ 加载用户策略代码代码 """

    def __init__(self, path):
        self.code_dir, self.code_file = os.path.split(path)

        if self.code_dir == "":
            self.code_dir = "."

    def load(self):
        sys.path.insert(0, self.code_dir)

        module_name = self.code_file.split(".")[0]
        module = importlib.import_module(module_name)
        return module
