#!/usr/bin/env python
#coding: utf-8
#
# File Name: tweetyshell.py
#
# Description:
#
# Creation Date: 2012-01-09
#
# Last Modified: 2012-04-03 16:14
#
# Created By: Daniël Franke <daniel@ams-sec.org>
#

import ipdb
import sys
import os


path = os.path.realpath(__file__)
sys.path.extend(path + "/..")

from libweetwit.twitter import Twitter

# VERY messy for now.
# TODO: Clean up.
if len(sys.argv) != 2:
    print "No storage directory given."
    sys.exit(2)

storage = sys.argv[1]

if not os.path.isdir(storage):
    print "%s is not a directory." % storage
    sys.exit(3)

twitter = Twitter(storage_dir=storage)

ipdb.set_trace()
