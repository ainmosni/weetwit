#!/usr/bin/env python
#coding: utf-8
#
# File Name: timeline.py
#
# Description: The main timeline listener for weetwit's timelined.
#
# Creation Date: 2012-03-05
#
# Last Modified: 2012-03-28 14:01
#
# Created By: Daniël Franke <daniel@ams-sec.org>

import os

from time import time

from tweepy import StreamListener
from libweetwit.exceptions import TwitterError

class TimeLineListener(StreamListener):

    def __init__(self, status_dir, timeout_count=3):
        # Set the reset counter and the amount of retries we want.
        self.timeout_count = timeout_count
        self.error_count = 0
        self.status_dir = status_dir
        super(TimeLineListener,self).__init__()

    def on_data(self, data):
        """
        Catch all the data and write it to loose files, we don't handle
        anything else.
        """
        # Reset the error counter.
        self.error_count = 0

        # Filter out favourite events.
        if '"event":"favorite"' in data:
            pass

        elif 'in_reply_to_status_id' in data:
            written = False
            while not written:
                # We use the timestamp as the filename because we don't want to
                # do any status parsing here.
                (seconds, millis) = str(time()).split('.')
                if len(millis) < 2:
                    millis += "0"
                ts = seconds + millis
                status_file = os.path.join(self.status_dir, ts + ".status")
                tmpfile = status_file + ".tmp"
                if not os.path.exists(status_file) and \
                        not os.path.exists(tmpfile):
                    with open(tmpfile, "w") as f:
                        f.write(data)
                    os.rename(tmpfile, status_file)
                    written = True

    def on_timeout(self):
        """We want to keep retrying for self.retry_count amount of times."""
        self.error_count += 1
        if self.error_count > self.timeout_count:
            raise TwitterError("Connection timed out for %s times." %
                    self.error_count)

        return True

    def on_error(self, status_code):
        """Handle errors."""
        if status_code == 420:
            raise TwitterError(
                    "Too many searches open, please close one and try again.")
        return True
