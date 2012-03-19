#!/usr/bin/env python
#coding: utf-8
#
# File Name: tweet.py
#
# Description: An enhanced status class.
#
# Creation Date: 2012-02-21
#
# Last Modified: 2012-03-14 22:44
#
# Created By: Daniël Franke <daniel@ams-sec.org>

from tweepy.models import Status

from libweetwit.utils import unescape

class Tweet(Status):
    """
        An enhanced status class, adds some helper functions and encapsulates
        some repeated code.
    """

    @classmethod
    def parse(cls, api, json):
        """Add some stuff to the parse routine."""
        status = super(Tweet, cls).parse(api, json)
        try:
            tid = status.retweeted_status.id
            txt = status.retweeted_status.text
            name = status.retweeted_status.user.name
            screen_name = status.retweeted_status.user.screen_name
            is_retweet = True
        except AttributeError:
            tid = status.id
            txt = status.text
            name = status.user.name
            screen_name = status.user.screen_name
            is_retweet = False
        rtname = status.user.name
        rtscreen_name = status.user.screen_name
        setattr(status, 'tid', tid)
        setattr(status, 'txt_unescaped', unescape(txt))
        setattr(status, 'name', unescape(name))
        setattr(status, 'screen_name', screen_name)
        setattr(status, 'rtname', unescape(rtname))
        setattr(status, 'rtscreen_name', rtscreen_name)
        setattr(status, 'is_retweet', is_retweet)
        setattr(status, 'txt', status.expand_urls(status.txt_unescaped))
        return status


    def expand_urls(self, text):
        """Expands the URLs in the text."""
        try:
            url_list = self.retweeted_status.entities['urls']
        except AttributeError:
            try:
                url_list = self.entities['urls']
            except AttributeError:
                return text

        for url in url_list:
            try:
                replacement = "%s [%s]" % (url['display_url'], url['url'])
                text = text.replace(url['url'], replacement)
            except TypeError:
                pass
        return text

