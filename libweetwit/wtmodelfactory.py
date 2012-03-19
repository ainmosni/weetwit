#!/usr/bin/env python
#coding: utf-8
#
# File Name: wtmodelfactory.py
#
# Description: An override of the normal weetwit model_factory.
#
# Creation Date: 2012-02-21
#
# Last Modified: 2012-03-13 21:06
#
# Created By: Daniël Franke <daniel@ams-sec.org>

from tweepy.models import ModelFactory

from libweetwit.tweet import Tweet
from libweetwit.tweep import Tweep

class wtModelFactory(ModelFactory):
    """Simple override to get our custom status class to be used in the API"""
    status = Tweet
    user = Tweep
