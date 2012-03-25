#!/usr/bin/env python
#coding: utf-8
#
# File Name: weetwit.py
#
# Description: Plugin to show latest tweets in weechat.
#
# Creation Date: 2012-01-05
#
# Last Modified: 2012-03-25 11:43
#
# Created By: Daniël Franke <daniel@ams-sec.org>

# TODO:
#   - Add conversation command, to automatically follow a conversation.
#

import os
import sys

import tweepy
import weechat as wc

import time

# Very ugly hack to kill all unicode errors with fire.
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    from libweetwit.db import DB
    from libweetwit.twitter import Twitter
    from libweetwit.exceptions import TwitterError
    from libweetwit.statusmonitor import StatusMonitor
    from libweetwit.utils import which
except ImportError:
    raise Exception(
      "Can't load needed modules, please install the libweetwit package!"
    )


SCRIPT_NAME         = "weetwit"
SCRIPT_AUTHOR       = "Daniël Franke <daniel@ams-sec.org>"
SCRIPT_VERSION      = "0.6.3"
SCRIPT_LICENSE      = "BSD"
SCRIPT_DESC         = "Full twitter suite for Weechat."

reload(sys)
sys.setdefaultencoding('utf-8')

twitter = False
db = False

def utcdt_to_lts(dt):
    """Converts a UTC datetime object to a local timezone int."""
    timestamp = time.mktime(dt.timetuple())
    if time.localtime().tm_isdst:
        timestamp += 3600
    timestamp -= time.timezone
    return timestamp

def get_own_buffer():
    """Returns the ID of our own buffer"""
    return wc.buffer_search("python", "weetwit")

def print_to_current(message, timestamp=0):
    """Prints a no logging message to the current buffer."""
    wc.prnt_date_tags(wc.current_buffer(), timestamp, "nolog,notify_status_update", message)

def print_to_buffer(message, timestamp=0):
    """Prints a message to the private buffer."""
    buf = get_own_buffer()
    wc.prnt_date_tags(buf, timestamp, "notify_message", message)

def print_error(message):
    """Prints a red error message to the current buffer."""
    print_to_current("%s%s" % (wc.color("*red"), message))

def print_success(message):
    """Prints a green success message to the current buffer."""
    print_to_current("%s%s" % (wc.color("*green"), message))

def add_to_nicklist(nick):
    """Add nick to the nicklist."""
    wc.nicklist_add_nick(get_own_buffer(), "", nick, 'bar_fg', '', '', 1)

def remove_from_nicklist(nick):
    """Remove nick from the nicklist."""
    nick_ptr = wc.nicklist_search_nick(get_own_buffer(), "", nick)
    wc.nicklist_remove_nick(get_own_buffer(), nick_ptr)


def display_tweet_details(tweet):
    """Displays details about a particular tweet."""
    print_to_current("%s-------------------" % wc.color("magenta"))
    print_to_current("%sTweet ID\t%s" % (wc.color("*cyan"), tweet.tid))
    print_to_current("%sBy\t%s (@%s)" % (wc.color("*cyan"), tweet.name,
        tweet.screen_name))
    print_to_current("%sTweet\t%s" % (wc.color("*cyan"), tweet.txt))
    if tweet.is_retweet:
        print_to_current("%sRetweeted By\t%s (@%s)" % (wc.color("*cyan"),
            tweet.rtname, tweet.rtscreen_name))
    if tweet.in_reply_to_status_id:
        print_to_current("%sReply To\t%s" % (wc.color("*cyan"),
            tweet.in_reply_to_status_id))
    print_to_current("%s-------------------" % wc.color("magenta"))



def timeline_cb(data, remaining_calls):
    """
    Displays the timeline.
    """
    global db
    global twitter
    buf = get_own_buffer()
    show_in_cur = wc.config_get_plugin("show_in_current")
    status_dir = wc.config_get_plugin("storage_dir") + "/statuses/"
    # Use the normal id here so that we can look up who retweeted it.
    try:
        for tweet in StatusMonitor(status_dir, twitter.api):
            if wc.current_buffer() != buf and \
                wc.config_string_to_boolean(show_in_cur):
                print_to_current(u"""%s@%s\t%s%s""" %
                    (wc.color('*cyan'),
                    tweet.screen_name,
                    wc.color("*cyan"),
                    tweet.txt),
                    timestamp=int(utcdt_to_lts(tweet.created_at)))

            tweep_color = wc.info_get("irc_nick_color", tweet.screen_name)
            print_to_buffer(u"""%s%s\t%s\n[#STATUSID: %s]""" %
                (tweep_color,
                tweet.screen_name,
                tweet.txt,
                tweet.id),
                timestamp=int(utcdt_to_lts(tweet.created_at)))

            db.set_last_tid(tweet.screen_name, tweet.id)
    except TwitterError as error:
        print_error(error)
    return wc.WEECHAT_RC_OK

def storage_cb(data, option, value):
    global db
    option = option.split('.')[-1]
    if option == 'storage_dir':
        if not os.path.exists(value):
            os.mkdir(value)
    db.set_config(option, value)

    return wc.WEECHAT_RC_OK

def tweet_cb(data, buffer, args):
    """Updates your twitter status."""
    global twitter
    tweet = args
    try:
        output = twitter.update_status(tweet)
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    print_success(output)
    return wc.WEECHAT_RC_OK


def tweet_info_cb(data, buffer, args):
    """Get information about a tweet."""
    global twitter
    try:
        tweet = twitter.get_tweet(args)
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    display_tweet_details(tweet)
    return wc.WEECHAT_RC_OK

def tweet_share_cb(data, buffer, args):
    """Share tweet with current IRC channel."""
    global twitter
    try:
        tweet = twitter.get_tweet(args)
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    message = '<@%s> %s [https://twitter.com/#!/%s/status/%s]' % \
        (tweet.screen_name, tweet.txt, tweet.screen_name, tweet.tid)
    wc.command(wc.current_buffer(), '/say %s' % message)
    return wc.WEECHAT_RC_OK


def retweet_cb(data, buffer, args):
    """
    Retweet a tweet, either by its TweetID or by @username, which then retweets
    the last tweet of @username. If a message follows the ID then we'll prepend
    that message to the message we're retweeting.
    """
    global twitter
    arg_list = args.split()
    try:
        tweet = twitter.get_tweet(arg_list[0])
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    try:
        if len(arg_list) > 1:
            msg = " ".join(arg_list[1:])
            msg += " RT @%s: %s" % (tweet.screen_name, tweet.txt_unescaped)
            output = twitter.update_status(msg)
        else:
            tweet.retweet()
            output = "Retweeted."
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    print_success(output)
    return wc.WEECHAT_RC_OK

def treply_cb(data, buffer, args):
    """Replies to an @username's last tweet or a specific TweetID."""
    global twitter
    arg_list = args.split()
    if len(arg_list) < 2:
        print_error("Need a recipient AND a message!")
        return wc.WEECHAT_RC_OK
    prefix = ''
    arg = arg_list[0]
    if arg.startswith("."):
        prefix = "."
        arg = arg.lstrip(".")
    msg = " ".join(arg_list[1:])
    try:
        tweet = twitter.get_tweet(arg)
        full_msg = "%s@%s %s" % (prefix, tweet.screen_name, msg)
        output = twitter.update_status(full_msg, tweet.tid)
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    print_success(output)
    return wc.WEECHAT_RC_OK

def show_user_cb(data, buffer, args):
    """Shows user's details."""
    global twitter
    try:
        user = twitter.get_user(args)
        tweet = twitter.get_tweet(user.status.id)
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    print_to_current("%s-------------------" % wc.color("magenta"))
    print_to_current("%sName\t%s (@%s)" % (wc.color("*cyan"),
        user.name,
        user.screen_name))
    print_to_current("%sDescription\t%s" % (wc.color("*cyan"), user.description))
    print_to_current("%sLocation\t%s" % (wc.color("*cyan"), user.location))
    print_to_current("%sURL\t%s" % (wc.color("*cyan"), user.url))
    print_to_current("%sStatus\t%s" % (wc.color("*cyan"),
        tweet.text))
    print_to_current("%sTweets\t%s" % (wc.color("*cyan"), user.statuses_count))
    print_to_current("%sFollows\t%s" % (wc.color("*cyan"), user.friends_count))
    print_to_current("%sFollowers\t%s" % (wc.color("*cyan"),
        user.followers_count))
    print_to_current("%sFollowing\t%s" % (wc.color("*cyan"), user.following))
    if user.verified:
        print_to_current("%sVerified!\t%s" % (wc.color("*yellow"),
            user.verified))
    print_to_current("%s-------------------" % wc.color("magenta"))
    return wc.WEECHAT_RC_OK


def follow_cb(data, buffer, args):
    """Follows @user."""
    global twitter
    try:
        user = twitter.get_user(args)
        user.follow()
    except (TwitterError, tweepy.TweepError) as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    add_to_nicklist(args)
    print_success("User @%s followed." % args)
    return wc.WEECHAT_RC_OK

def unfollow_cb(data, buffer, args):
    """Unfollows @user."""
    global twitter
    try:
        user = twitter.get_user(args)
        user.unfollow()
    except (TwitterError, tweepy.TweepError) as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    remove_from_nicklist(args)
    print_success("User @%s unfollowed." % args)
    return wc.WEECHAT_RC_OK


def timelined_cb(data, command, rc, stdout, stderr):
    """Very generic callback in case timelined acts weird."""
    print_to_current("%s***TIMELINED OUTPUT***" % wc.color("*red"))
    print_to_current("%sData\t%s" % (wc.color("*red"), data))
    print_to_current("%sCommand\t%s" % (wc.color("*red"), command))
    print_to_current("%sRC\t%s" % (wc.color("*red"), rc))
    print_to_current("%sStdout\t%s" % (wc.color("*red"), stdout))
    print_to_current("%sStderr\t%s" % (wc.color("*red"), stderr))

    return wc.WEECHAT_RC_OK

if wc.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, "", ""):

    loaded = False

    # Check if our buffer exists and if not, create it.
    buf = get_own_buffer()
    if not "0x" in buf:
        buf = wc.buffer_new("weetwit", "", "", "", "")
        wc.buffer_set(buf, "title", "Timeline")



    # Default options
    default_storage = wc.info_get("weechat_dir", '') + "/weetwit/"
    script_options = {
            "storage_dir" : default_storage,
            "consumer_key" : "",
            "consumer_secret" : "",
            "access_token" : "",
            "access_token_secret" : "",
            "show_in_current" : "false",
            "timelined_location" : "timelined"
    }
    for option, default_value in script_options.iteritems():
         if not wc.config_is_set_plugin(option):
             wc.config_set_plugin(option, default_value)

    storage_dir = wc.config_get_plugin("storage_dir")
    if not os.path.exists(storage_dir):
            os.mkdir(storage_dir)

    # Get a handle on our database.
    db = DB(storage_dir)

    # Save all options to the database.
    for option, default_value in script_options.iteritems():
        value = wc.config_get_plugin(option)
        if not value:
            value = "NULL"
        db.set_config(option, value)

    followed = False
    try:
        twitter = Twitter(db=db)
        followed = twitter.get_followed()
        loaded = True
    except TwitterError as error:
        print_error(error)
        print_error(
            "Please reload the plugin when the problem has been resolved."
        )
        loaded = False

    if loaded:
        # We want to highlight on our screen_name.
        screen_name = twitter.api.me().screen_name
        wc.buffer_set(buf, "highlight_words", screen_name)
        wc.buffer_set(buf, "nicklist", "1")

        # Add our own screen_name to the nicklist.
        add_to_nicklist(screen_name)
        # Fill the nicklist with all followed tweeps.
        for screen_name in followed:
            add_to_nicklist(screen_name)

        # Find timelined
        timelined = which(wc.config_get_plugin("timelined_location"))
        if not timelined:
            print_error(
                "Couldn't find timelined, please set 'plugins.var.python.weetwit.timelined"
            )

        # Get the python binary location and start timelined.
        python2_bin = wc.info_get('python2_bin', '') or 'python'
        weetwit_hook_process = wc.hook_process(
            python2_bin + " " + timelined[0]  +  " " + storage_dir,
            0, "timelined_cb", "")

        # Check if there are new timeline entries every second.
        wc.hook_timer(1 * 1000, 60, 0, "timeline_cb", "")

        # Config change hook.
        wc.hook_config("plugins.var.python." + SCRIPT_NAME + ".*",
            "storage_cb", "")

        # All commands
        hook = wc.hook_command("tweet", "Updates your twitter status.",
            "[tweet]",
            "The text to update with (140 characters max).",
            "",
            "tweet_cb", "")

        hook = wc.hook_command("tinfo", "Lookup info about a certain tweet.",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "tweet_info_cb", "")

        hook = wc.hook_command("treply", "Reply to a specific tweet",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "treply_cb", "")

        hook = wc.hook_command("retweet", "Retweet a specific tweet.",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "retweet_cb", "")

        hook = wc.hook_command("tshare", "Share a tweet with the current channel.",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "tweet_share_cb", "")

        hook = wc.hook_command("twhois", "Get information about a certain user",
            "@username",
            "The @username of the user you want information about.",
            "",
            "show_user_cb", "")

        hook = wc.hook_command("tfollow", "Follow a certain user",
            "@username",
            "The @username of the user you to follow.",
            "",
            "follow_cb", "")

        hook = wc.hook_command("tunfollow", "Unfollow a certain user",
            "@username",
            "The @username of the user you to unfollow.",
            "",
            "unfollow_cb", "")
