#!/usr/bin/env python
#coding: utf-8
#
# File Name: twitter.py
#
# Description:
#
# Creation Date: 2012-02-22
#
# Last Modified: 2013-06-17 23:42
#
# Created By: Daniël Franke <daniel@ams-sec.org>
#

import re

from collections import defaultdict

from tweepy.parsers import ModelParser
from tweepy import OAuthHandler, TweepError

from libweetwit.wtmodelfactory import wtModelFactory
from libweetwit.db import DB
from libweetwit.exceptions import TwitterError
from libweetwit.api import weetwitAPI as API


class Twitter(object):
    """A class that does all interactions with twitter."""
    def __init__(self, storage_dir=False, db=False):
        """Initialise the API."""
        if not db and not storage_dir:
            raise TypeError(
                "Twitter() needs either a storage_dir or a db argument."
            )

        if not db:
            db = DB(storage_dir)
        self.db = db
        ck = self.db.get_config('consumer_key')
        cs = self.db.get_config('consumer_secret')
        at = self.db.get_config('access_token')
        ats = self.db.get_config('access_token_secret')
        mf = wtModelFactory()
        pr = ModelParser(model_factory=mf)
        self.auth = OAuthHandler(ck, cs)
        self.auth.set_access_token(at, ats)
        self.api = API(self.auth, parser=pr)
        try:
            self.api.me().name
        except TweepError as error:
            raise TwitterError("Could not connect to Twitter: %s" % error)
        except TypeError as error:
            raise TwitterError("Your keys haven't been set correctly!")

    def update_status(self, message, reply_id=False):
        """Posts text to twitter."""
        if self.__is_sane(message):
            try:
                self.api.update_status(message, in_reply_to_status_id=reply_id)
            except TweepError as error:
                raise TwitterError("Failed to post status: %s" % error)
            return "Status updated."
        else:
            raise TwitterError("Status too long!")

    def get_tweet(self, identification):
        """Return a tweet from either an integer or cached screen name."""
        tid = False
        try:
            int(identification)
            tid = identification
        except ValueError:
            identification = identification.lstrip("@")
            tid = self.db.get_last_tid(identification)
            if not tid:
                raise TwitterError("ID %s not cached." % identification)
        try:
            return self.api.get_status(tid, include_entities=True)
        except TweepError as error:
            raise TwitterError("Failed to get tweet: %s" % error)

    def get_user(self, user):
        """Returns the requested user."""
        try:
            user = self.api.get_user(user, include_entities=True)
        except TweepError as error:
            raise TwitterError("Failed to get user: %s" % error)
        return user

    def get_followed(self):
        """Returns an array of screen_names that you follow."""
        try:
            followed = [u.screen_name for u in self.api.friends()]
        except TweepError as error:
            raise TwitterError("Faled to get followed: %s" % error)
        return followed

    def get_trend_places(self):
        """
        Returns a dict of dicts, first by country then by place.
        Every country has a special 'woeid' key that holds the woeid of the
        country itself and all the places of the country pointing to their
        respective woeids.
        A special exception is the 'Worldwide' "country" which only has a
        woeid entry.
        """
        try:
            trend_places = self.api.trends_available()
        except TweepError as error:
            raise TwitterError("Falied to get available places: %s." % error)

        places = defaultdict(dict)
        for place in trend_places:
            if not place['country']:
                places['Worldwide'] = {'woeid': place['woeid']}
            else:
                if place['country'] == place['name']:
                    places[place['country']]['woeid'] = place['woeid']
                else:
                    places[place['country']][place['name']] = place['woeid']
        return places

    def get_trends(self, woeid):
        """
        Gets the current trends for the location represented by woeid.
        Returns a list of trends with element 0 representing the location name.
        """
        try:
            trend_response = self.api.trends_place(woeid)
        except TweepError as error:
            raise TwitterError("Failed to get trends: %s" % error)

        trends = []
        trends.append(trend_response[0]['locations'][0]['name'])
        for trend in trend_response[0]['trends']:
            trends.append(trend['name'])

        return trends

    def get_favorites(self):
        """Get your favourite tweets."""
        try:
            favorites = self.api.favorites(include_entities=True)
        except TweepError as error:
            raise TwitterError("Failed to get favourites: %s" % error)
        return favorites

    def status_count(self, message):
        """
        Replaces the URLs and returns the length how twitter would count it.
        """
        message = self.__replace_urls(message)
        return(len(message))

    def __is_sane(self, message):
        """Does sanity checks to see if the status is valid."""
        if self.status_count(message) > 140:
            return False
        return True

    def __replace_urls(self, message):
        """Replace URLs with placeholders, 20 for http URLs, 21 for https."""
        # regexes to match URLs
        octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
        ip_addr = r'%s(?:\.%s){3}' % (octet, octet)
        # Base domain regex off RFC 1034 and 1738
        label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
        domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
        url_re = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' %
                            (domain, ip_addr), re.I)

        new_message = message

        for url in url_re.findall(message):
            short_url = 'x' * 20
            if url.startswith('https'):
                short_url = 'x' * 21
            new_message = new_message.replace(url, short_url)

        return new_message
