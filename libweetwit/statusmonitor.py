#!/usr/bin/env python
#coding: utf-8
#
# File Name: statusmonitor.py
#
# Description:
#
# Creation Date: 2012-03-13
#
# Last Modified: 2012-03-13 22:41
#
# Created By: Daniël Franke <daniel@ams-sec.org>

import glob
import json
import os

from libweetwit.tweet import Tweet

class StatusMonitor(object):
    """
        An iterator that takes all status files and generates a new Tweet every
        iteration.
    """
    def __init__(self, status_dir, api):
        "Gets all the statuses, sorts them and puts them in a list."
        pattern = status_dir + "/*.status"
        self.status_files = glob.glob(pattern)
        self.status_files.sort()
        self.status_files.reverse()
        self.api = api

    def __iter__(self):
        return self

    def next(self):
        "Returns the next status."
        try:
            status_file = self.status_files.pop()
            with file(status_file) as f:
                status = Tweet.parse(self.api, json.loads(f.read()))
            os.unlink(status_file)
            return status
        except IndexError:
            raise StopIteration()
