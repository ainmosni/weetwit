#!/usr/bin/env python
#coding: utf-8
#
# File Name: timeline.py
#
# Description: The main timeline listener for weetwit's timelined.
#
# Creation Date: 2012-03-05
#
# Last Modified: 2012-03-15 17:15
#
# Created By: Daniël Franke <daniel@ams-sec.org>

import os

from time import time

from tweepy import StreamListener

class TimeLineListener(StreamListener):

    def __init__(self, status_dir):
        self.status_dir = status_dir
        super(TimeLineListener,self).__init__()

    def on_data(self, data):
        """
        Catch all the data and write it to loose files, we don't handle
        anything else.
        """
        if ''',"event":"favorite"}''' in data:
            return

        if 'in_reply_to_status_id' in data:
            written = False
            while not written:
                # We use the timestamp as the filename because we don't want to
                # do any status parsing here.
                (seconds, millis) = str(time()).split('.')
                if len(millis) < 2:
                    millis += "0"
                ts = seconds + millis
                status_file = self.status_dir + "/" + ts + ".status"
                tmpfile = status_file + ".tmp"
                if not os.path.exists(status_file) and \
                        not os.path.exists(tmpfile):
                    with open(tmpfile, "w") as f:
                        f.write(data)
                    os.rename(tmpfile, status_file)
                    written = True

