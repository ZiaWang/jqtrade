# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages


THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_package_info(item, default=None):
    scope = {}

    data = None
    file = os.path.join(THIS_DIR, "jqtrade", "__init__.py")
    if os.path.exists(file):
        with open(file) as fp:
            exec(fp.read(), scope)
        data = scope.get(item)

    return data or default


def get_long_description():
    with open(os.path.join(THIS_DIR, "README.md"), "rb") as f:
        long_description = f.read().decode("utf-8")
    return long_description


def _parse_requirement_file(path):
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        requirements = [line.strip() for line in f if line.strip()]
    return requirements


def get_install_requires():
    requirement_file = os.path.join(THIS_DIR, "requirements.txt")
    return _parse_requirement_file(requirement_file)


author = get_package_info("__author__"),
email = get_package_info("__email__")


setup(
    name="jqtrade",
    version=get_package_info("__version__"),
    description="Simple trading framework for Quant",
    packages=find_packages(exclude=("tests", "tests.*")),
    author=author,
    author_email=email,
    maintainer=author,
    maintainer_email=email,
    license="MIT License",
    package_data={'': ['*.*']},
    url="https://github.com/ZiaWang/jqtrade",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    install_requires=get_install_requires(),
    zip_safe=False,
    platforms=["all"],
    python_requires=">=3.6.2, <=3.9.18",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "console_scripts": [
            "jqtrade = jqtrade.__main__:main",
        ],
    },
)
