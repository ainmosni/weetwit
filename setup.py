#!/usr/bin/env python
#coding: utf-8
#
# File Name: setup.py
#
# Description: Setup file for the weetwit method.
#
# Creation Date: 2012-03-13
#
# Last Modified: 2012-03-19 16:38
#
# Created By: Daniël Franke <daniel@ams-sec.org>
from distutils.core import setup

setup(
    name='weetwit',
    version='0.5',
    author='Daniël Franke',
    author_email='daniel@ams-sec.org',
    packages=['libweetwit'],
    scripts=['bin/timelined',],
    license='LICENSE.txt',
    description='Support module for the weechat plugin "weetwit".',
    long_description=open('README.rst').read(),
    install_requires=["tweepy >= 1.8"])

