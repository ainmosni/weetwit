#!/usr/bin/env python
#coding: utf-8
#
# File Name: tweep.py
#
# Description:
#
# Creation Date: 2012-03-06
#
# Last Modified: 2012-04-12 11:53
#
# Created By: Daniël Franke <daniel@ams-sec.org>


from tweepy.models import User

from libweetwit.utils import unescape

class Tweep(User):
    """
        An enhanced User class, unescapes data.
    """

    @classmethod
    def parse(cls, api, json):
        user = super(Tweep, cls).parse(api, json)
        user.name = unescape(user.name)
        user.description = unescape(user.description)
        user.location = unescape(user.location)
        return user

    def report_spam(self):
        """Reports the user for spam."""
        return self._api.report_spam(self.id)
