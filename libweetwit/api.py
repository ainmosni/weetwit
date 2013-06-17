#!/usr/bin/env python
#coding: utf-8
#
# File Name: api.py
#
# Description: Monkeypatch for the tweepy API to repatch friends in.
#
# Creation Date: 2013-06-17
#
# Last Modified: 2013-06-17 23:43
#
# Created By: Daniël Franke <daniel@ams-sec.org>

from tweepy import API
from tweepy.binder import bind_api


class weetwitAPI(API):
    """
    Patched twitter API.
    """

    friends = bind_api(
        path = '/friends/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )
