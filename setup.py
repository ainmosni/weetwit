#!/usr/bin/env python
#coding: utf-8
#
# File Name: setup.py
#
# Description: Setup file for the weetwit method.
#
# Creation Date: 2012-03-13
#
# Last Modified: 2013-06-17 23:50
#
# Created By: Daniël Franke <daniel@ams-sec.org>
import os
from distutils.core import setup

# Utility function copied from the example project.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='weetwit',
    version='0.10.2',
    author=u'Daniël Franke',
    author_email='daniel@ams-sec.org',
    packages=['libweetwit'],
    scripts=['bin/timelined',],
    license='LICENSE.txt',
    keywords='weechat twitter',
    url='https://github.com/ainmosni/weetwit',
    description='Twitter suite for Weechat.',
    long_description=read("README.rst"),
    install_requires=["tweepy>=2.0"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console :: Curses",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX"])

