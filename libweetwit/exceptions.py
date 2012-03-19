#!/usr/bin/env python
#coding: utf-8
#
# File Name: exceptions.py
#
# Description:
#
# Creation Date: 2012-03-13
#
# Last Modified: 2012-03-13 20:57
#
# Created By: Daniël Franke <daniel@ams-sec.org>

class TwitterError(Exception):
    """The main exception class."""
    def __init__(self, arg):
        self.error = arg

    def __str__(self):
        return self.error
        
