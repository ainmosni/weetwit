====================================
weetwit: A twitter suite for weechat
====================================

**As everyone already noticed, development on this stopped quite a while ago.**

*author*
    Daniël Franke (@ainmosni) <daniel[at]ams-sec[dot]org>

Welcome to the wonderful world of weetwit, a plugin that will transform weechat
to a (soon-to-be) fully-featured twitter client.

Features
========

* Realtime streaming timeline.
* Realtime search.
* Trending support.
* Tweet length counter.
* Favourite support.
* Updating, replying and retweeting according to Twitter standards.
* Aware of twitter URL shortening.
* Tools to query users and status updates.
* Able to (un-)follow directly from weechat.
* Report spammers directly from weechat.
* Share updates with IRC.
* Conversation support


Installation
============

Before you can use it, you have to "create" a new application at twitter, the
reason for this is that I can't include the application keys without them
becoming public knowledge. You can create the application at `Twitter
<http://dev.twitter.com>`_. The application needs read/write access.

First we need to install the module:

Installation through pip, note that you must get the plugin seperately.::

    # pip install weetwit
    $ Copy the plugin to ~/.weechat/python

Installation from source::

    # cd /path/to/source/files
    # pip install tweepy
    # python setup.py install
    $ cp plugin/weetwit.py ~/.weechat/python

Configuration of weechat::

    ] /python load weetwit.py
    ] /set plugins.var.python.weetwit.access_token access_token_goes_here
    ] /set plugins.var.python.weetwit.access_token_secret access_token_secret_goes_here
    ] /set plugins.var.python.weetwit.consumer_key consumer_key_goes_here
    ] /set plugins.var.python.weetwit.consumer_secret consumer_secret_goes_here
    ] /python reload weetwit

You should now have a running weetwit.

Configuration parameters
========================

There are multiple configuration parameters you can alter, here is a short
description of them.

* **plugins.var.python.weetwit.show_in_current**: Show the timeline in the
  current window.
* **plugins.var.python.weetwit.current_while_away**: Show the timeline in the
  current window while away.
* **plugins.var.python.weetwit.current_while_detached**: Show the timeline in the
  current window while screen/tmux detached.
* **plugins.var.python.weetwit.current_color**: The color of the tweets in the
  current buffer.
* **plugins.var.python.weetwit.storage_dir**: The location of where all the
  weetwit related files will be kept.
* **plugins.var.python.weetwit.timelined_location**: The location of the
  timelined monitoring daemon.
* **plugins.var.python.weetwit.trend_woeid**: The woeid you want to see trends
  for, defaults to worldwide.
* **plugins.var.python.weetwit.nick_color**: The color of @names. Use
  'nick_color' if you want people colored uniquely.
* **plugins.var.python.weetwit.hash_color**: The color of #hashtags.
* **plugins.var.python.weetwit.mention_color**: The color that @people
  mentioned in tweets should have.
* **rt_style**: How RTs are displayed. 'postfix' will show the retweeter after
  the tweet like this (RT by @username) 'prefix' will show the retweeter before
  the tweet.
* **expand_urls**: Expand URLs, when this is on, it will show a preview of the
  URL before the t.co URL, if off it will only show the t.co url.


Bar items
=========

* **tweet_counter** Shows the amount of characters that are typed into the
  timeline buffer, it's aware of t.co URL shortening.

Weechat commands
================

Many commands take <status identification> as argument, this can either be the
ID of the status or a screen_name. In case of the screen_name, we will use the
ID of last status by screen_name. (Note: if screen_name hasn't showed up in your
timeline, this won't work.)

* \/tweet <status>
    - Update your status, this can be 140 characters long. URLs will be shortened 
      using t.co by twitter. You don't need this command on the dedicated
      timeline buffer.

* \/tinfo <status identification>
    - Shows more detailed information about a status update.

* \/treply [.]<status identification> <message>
    - Replies to the relevant status update, this will always start with the
      @screen_name of the person the status belonged to, if the identification is
      prefixed with a dot, a dot will be prepended to the message so that your
      other followers will see it as well.

* \/tconversation <status identification>
    - Displays the conversation leading up this status update.

* \/tfavorite <status identification>
    - Favourites a status update.

* \/tunfavorite <status identification>
    - Removes a tweet from your favourites.

* \/tfavorites
    - Shows your favourited tweets.


* \/retweet <status identification> [message]
    - Retweets the relevant status update, if [message] is present this will
      prepended to the retweet.

* \/tsearch <keywords>
    - Opens a new buffer with a realtime search of <keywords>, you can only
      have a limited amount open of these at one time, opening more might stop
      already existing searches.

* \/tshare <status identification>
    - Shares the relevant status update with the current IRC channel.

* \/twhois <screen_name>
    - Displays information about screen_name.

* \/tfollow <screen_name>
    - Follows screen_name.

* \/tunfollow <screen_name>
    - Unfollows screen_name.

* \/trending [woeid]
    - Displays what's trending in the location represented by [woeid].
      If no woeid present it uses the woeid set at
      plugins.var.python.weetwit.trend_woeid.

* \/travail
    - Displays woeids of available trend locations.

* \/treport [--yes] <screen_name>
    - Reports <screen_name> for spam. If --yes isn't added, the user won't be
      reported for spam.

FAQ
===

    :Q: Why does your script spawn an extra python process?
    :A: Because weechat doesn't support background threads, and blocks on long
        running operations, this process is what monitors your timeline.


    :Q: I don't want those ugly STATUSIDs in my weetwit buffer.
    :A: Add a filter like this: "/filter add statusid python.timeline * \\[#STATUSID:"
        now you can toggle between them hidden and visible, depending on your
        needs.
