#!/usr/bin/env python
# coding: utf-8
"""
Python Dubbo Library
"""
from setuptools import setup, find_packages
import os

setup(
    name = "python-dubbo",
    version = "0.0.1",
    description = (
        "Python Dubbo Library"
    ),
    long_description = open('README.md').read(),
    author = "nobody",
    author_email = 'nobody',
    packages = find_packages(exclude=['tests', 'tests.*']),
    install_requires = ["kazoo>=2.0", "jsonrpclib>=0.1.3"],
)
