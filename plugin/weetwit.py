#!/usr/bin/env python
#coding: utf-8
#
# File Name: weetwit.py
#
# Description: Plugin to show latest tweets in weechat.
#
# Creation Date: 2012-01-05
#
# Last Modified: 2014-04-28 15:35
#
# Created By: Daniël Franke <daniel@ams-sec.org>
# Modified by: Tor Hveem <tor@hveem.no>

# TODO:
#   - Add conversation command, to automatically follow a conversation.
#

import os
import sys
import time
import re

from hashlib import md5

import tweepy
import weechat as wc


# Very ugly hack to kill all unicode errors with fire.
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    from libweetwit.db import DB
    from libweetwit.twitter import Twitter
    from libweetwit.exceptions import TwitterError
    from libweetwit.statusmonitor import StatusMonitor
    from libweetwit.utils import which, kill_process
except ImportError:
    raise Exception(
      "Can't load needed modules, please install the libweetwit package!"
    )


SCRIPT_NAME         = "weetwit"
SCRIPT_AUTHOR       = "Daniël Franke <daniel@ams-sec.org>"
SCRIPT_VERSION      = "0.10.2"
SCRIPT_LICENSE      = "BSD"
SCRIPT_DESC         = "Full twitter suite for Weechat."

reload(sys)
sys.setdefaultencoding('utf-8')

# Some global objects
twitter = False
db = False
user = False
hooks = {}
tlid = {}
buffers = {}

def utcdt_to_lts(dt):
    """Converts a UTC datetime object to a local timezone int."""
    timestamp = time.mktime(dt.timetuple())
    if time.localtime().tm_isdst:
        timestamp += 3600
    timestamp -= time.timezone
    return timestamp

def print_to_current(message, timestamp=0):
    """Prints a no logging message to the current buffer."""
    wc.prnt_date_tags(wc.current_buffer(), timestamp, "nolog,notify_status_update", message)

def print_to_buffer(buf, message, timestamp=0):
    """Prints a message to the private buffer."""
    wc.prnt_date_tags(buf, timestamp, "notify_message", message)

def print_error(message):
    """Prints a red error message to the current buffer."""
    print_to_current("%s%s" % (wc.color("*red"), message))

def print_success(message):
    """Prints a green success message to the current buffer."""
    print_to_current("%s%s" % (wc.color("*green"), message))

def add_to_nicklist(buf, nick):
    """Add nick to the nicklist."""
    wc.nicklist_add_nick(buf, "", nick, wc.info_get('irc_nick_color_name', nick), '', '', 1)

def remove_from_nicklist(buf, nick):
    """Remove nick from the nicklist."""
    nick_ptr = wc.nicklist_search_nick(buf, "", nick)
    wc.nicklist_remove_nick(buf, nick_ptr)


def display_tweet_details(tweet):
    """Displays details about a particular tweet."""
    print_to_current("%s-------------------" % wc.color("magenta"))
    print_to_current("%sTweet ID\t%s" % (wc.color("*cyan"), tweet.tid))
    print_to_current("%sBy\t%s (@%s)" % (wc.color("*cyan"), tweet.name,
        tweet.screen_name))
    expand_urls = wc.config_string_to_boolean(wc.config_get_plugin("expand_urls"))
    text = tweet.txt_unescaped
    if expand_urls:
        text = tweet.txt
    print_to_current("%sTweet\t%s" % (wc.color("*cyan"), text))
    print_to_current("%sClient\t%s" % (wc.color("*cyan"), tweet.source))
    if tweet.favorited:
        print_to_current("%sFavourite\t%s" % (wc.color("*cyan"),
            tweet.favorited))
    if tweet.is_retweet:
        print_to_current("%sRetweeted By\t%s (@%s)" % (wc.color("*cyan"),
            tweet.rtname, tweet.rtscreen_name))
    if tweet.in_reply_to_status_id:
        print_to_current("%sReply To\t%s" % (wc.color("*cyan"),
            tweet.in_reply_to_status_id))
    print_to_current("%s-------------------" % wc.color("magenta"))

def is_attached():
    """
    Check if screen/tmux is attached.
    """
    # Code generously donated by Tor Hveem, relicensed to BSD with permission.
    sock = False
    if 'STY' in os.environ.keys():
        # We're in screen
        cmd_output = os.popen('env LC_ALL=C screen -ls').read()
        match = re.search(r'Sockets? in (/.+)\.', cmd_output)
        if match:
            sock = os.path.join(match.group(1), os.environ['STY'])

    if not sock and 'TMUX' in os.environ.keys():
        # We're in tmux
        socket_data = os.environ['TMUX']
        sock = socket_data.rsplit(',', 2)[0]

    if not sock:
        # If we didn't find anything, we're always attached.
        return True

    attached = os.access(sock, os.X_OK)
    if attached:
        return True

    return False

def display_cb(data, remaining_calls):
    """
    Displays the timeline
    """
    global db
    global twitter
    global buffers
    global tlid
    default_color = wc.color("default")
    show_in_cur = "Off"
    cur_away = "On"
    cur_detached = "On"
    valid_buffers = []
    valid_buffers.append(buffers[data])
    current_buffer = wc.current_buffer()
    expand_urls = wc.config_string_to_boolean(wc.config_get_plugin("expand_urls"))
    show_in_cur = wc.config_string_to_boolean(wc.config_get_plugin("show_in_current"))
    cur_away = wc.config_string_to_boolean(wc.config_get_plugin("current_while_away"))
    cur_detached = wc.config_string_to_boolean(wc.config_get_plugin("current_while_detached"))
    away = wc.buffer_get_string(current_buffer, 'localvar_away')

    # I have NO idea why is doesn't work here but this does so... what?
    if (
        "__TIMELINE" in data
        and show_in_cur
        and buffers[data] != current_buffer
        and (not away or cur_away)
        and (is_attached() or cur_detached)
       ):
        valid_buffers.append(current_buffer)
    status_dir = os.path.join(wc.config_get_plugin("storage_dir"),
            tlid[data])
    try:
        for tweet in StatusMonitor(status_dir, twitter.api):

            nick_color = wc.info_get("irc_nick_color", tweet.screen_name)
            for buf in valid_buffers:
                screen_name = nick_color + tweet.screen_name

                text = tweet.txt_unescaped
                if expand_urls:
                    text = tweet.txt
                text_color = default_color
                if buf is current_buffer:
                    text_color = cur_color = wc.color(wc.config_get_plugin("current_color"))
                    screen_name = cur_color + screen_name
                    text = cur_color + text

                # Use the nick coloring hashing for hash colors so hashes get consistant and different coloring
                def hashcolor(m):
                    s = m.group(0)
                    return "{}{}{}".format(wc.info_get("irc_nick_color", s), s, text_color)
                text = re.sub(r'(?P<hash>#\w+)', hashcolor, text)

                retweet_style = wc.config_get_plugin("rt_style")

                output =""
                if tweet.is_retweet:
                    retweeter = "@%s" % (tweet.rtscreen_name)
                    if retweet_style == 'postfix':
                        output = '%s\t%s%s (RT by %s%s)' % (screen_name,
                                                            text_color,
                                                            text,
                                                            retweeter,
                                                            text_color)
                    else:
                        output = "%s\tRT %s%s %s" % (retweeter,
                                                     screen_name,
                                                     text_color,
                                                     text)
                else:
                    output = u"%s\t%s" % (screen_name, text)

                output += "\n[#STATUSID: %s]" % tweet.id

                print_to_buffer(buf, output)

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

def conversation_cb(data, buffer, args):
    """
    Follows the reply trail until the original was found.
    NOTE: This might block for a while.
    """
    global twitter
    conversation = []
    reply_id = args
    # Loop as long as there was a reply_id.
    while reply_id:
        try:
            conversation.append(twitter.get_tweet(reply_id))
            reply_id = conversation[-1].in_reply_to_status_id
        except TwitterError as error:
            print_error(error)
            break
    if conversation:
        # Reverse the conversation to get the oldest first.
        conversation.reverse()
        # Now display the conversation.
        print_to_current("%s-------------------" % wc.color("magenta"))
        for tweet in conversation:
            nick_color = wc.info_get("irc_nick_color", tweet.screen_name)
            screen_name = nick_color + tweet.screen_name
            expand_urls = wc.config_string_to_boolean(wc.config_get_plugin("expand_urls"))
            text = tweet.txt_unescaped
            if expand_urls:
                text = tweet.txt
            output = "%s\t%s" % (screen_name, text)
            if tweet.is_retweet:
                output += " (RT by @%s)" % tweet.rtscreen_name
            output += "\n[#STATUSID: %s]" % tweet.id
            print_to_current(output)
        print_to_current("%s-------------------" % wc.color("magenta"))
    return wc.WEECHAT_RC_OK

def show_favorites_cb(data, buffer, args):
    """
    Show all the tweets that are favourited by the user.
    """
    global twitter
    try:
        favs = twitter.get_favorites()
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    if favs:
        print_to_current("%sFAVOURITES\t%s-------------------" %
                (wc.color("yellow"), wc.color("magenta")))
        for fav in favs:
            nick_color = wc.info_get("irc_nick_color", fav.screen_name)
            screen_name = nick_color + fav.screen_name
            expand_urls = wc.config_string_to_boolean(wc.config_get_plugin("expand_urls"))
            text = fav.text_unescaped
            if expand_urls:
                text = fav.text
            output = "%s\t%s" % (screen_name, text)
            if fav.is_retweet:
                output += " (RT by @%s)" % fav.rtscreen_name
            output += "\n[#STATUSID: %s]" % fav.id
            print_to_current(output)
        print_to_current("%s-------------------" % wc.color("magenta"))
    return wc.WEECHAT_RC_OK

def tweet_favorite_cb(data, buffer, args):
    """Add a tweet to your favourites."""
    global twitter
    try:
        tweet = twitter.get_tweet(args)
        tweet.favorite()
    except (TwitterError, TwitterError) as error:
        print_error("Couldn't favourite tweet: %s" % error)
        return wc.WEECHAT_RC_OK
    print_success("Tweet successfully favourited.")
    return wc.WEECHAT_RC_OK

def tweet_unfavorite_cb(data, buffer, args):
    """Remove a tweet from your favourites."""
    global twitter
    try:
        tweet = twitter.get_tweet(args)
        tweet.unfavorite()
    except (TwitterError, TwitterError) as error:
        print_error("Couldn't unfavourite tweet: %s" % error)
        return wc.WEECHAT_RC_OK
    print_success("Tweet successfully unfavourited.")
    return wc.WEECHAT_RC_OK

def tweet_share_cb(data, buffer, args):
    """Share tweet with current IRC channel."""
    global twitter
    try:
        tweet = twitter.get_tweet(args)
    except TwitterError as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    expand_urls = wc.config_string_to_boolean(wc.config_get_plugin("expand_urls"))
    text = tweet.txt_unescaped
    if expand_urls:
        text = tweet.txt
    message = '<@%s> %s [https://twitter.com/#!/%s/status/%s]' % \
        (tweet.screen_name, text, tweet.screen_name, tweet.tid)
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

def report_spam_cb(data, buffer, args):
    """Reports a user for spam."""
    global twitter
    arglist = args.split()
    if len(arglist) > 2:
        print_error("Too many arguments.")
        return wc.WEECHAT_RC_OK
    spammer = arglist[-1]
    try:
        user = twitter.get_user(spammer)
    except TwitterError as error:
        print_error("Can't get user: %s" % error)
        return wc.WEECHAT_RC_OK
    if arglist[0] != "--yes":
        print_error("Are you sure you want to report %s for spamming?" %
                user.name)
        print_error("If you are sure please confirm by typing /treport --yes %s" %
                args)
        return wc.WEECHAT_RC_OK
    try:
        user.report_spam()
    except TwitterError as error:
        print_error("Failed to report %s for spamming: " % (user.name, error))
        return wc.WEECHAT_RC_OK
    print_success("Successfully reported %s for spamming!" % user.name)
    return wc.WEECHAT_RC_OK


def follow_cb(data, buffer, args):
    """Follows @user."""
    global twitter
    global buffers
    try:
        user = twitter.get_user(args)
        user.follow()
    except (TwitterError, tweepy.TweepError) as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    add_to_nicklist(buffers['__TIMELINE'], args)
    print_success("User @%s followed." % args)
    return wc.WEECHAT_RC_OK

def unfollow_cb(data, buffer, args):
    """Unfollows @user."""
    global twitter
    global buffers
    try:
        user = twitter.get_user(args)
        user.unfollow()
    except (TwitterError, tweepy.TweepError) as error:
        print_error(error)
        return wc.WEECHAT_RC_OK
    remove_from_nicklist(buffers['__TIMELINE'], args)
    print_success("User @%s unfollowed." % args)
    return wc.WEECHAT_RC_OK

def trends_available_cb(data, buffer, args):
    """Shows the available trend locations."""
    global twitter
    try:
        places = twitter.get_trend_places()
    except TwitterError as error:
        print_error(error)
    print_to_current("%sWorldwide\t%s" % (wc.color("*cyan"),
        places['Worldwide']['woeid']))
    del(places['Worldwide'])
    print_to_current("\n")
    countries = sorted(places)
    for country in countries:
        print_to_current("%s%s\t%s" % (wc.color("*cyan"), country,
            places[country]['woeid']))
        del(places[country]['woeid'])
        print_to_current("%s------\t" % wc.color("magenta"))
        locations = sorted(places[country])
        for location in locations:
            print_to_current("%s%s\t%s" % (wc.color("cyan"), location,
                places[country][location]))
        print_to_current("\n")
    return wc.WEECHAT_RC_OK

def trends_cb(data, buffer, args):
    """
    Gets the trend for woeid or, if absent the trends for the configured woeid.
    """
    global twitter
    woeid = wc.config_get_plugin("trend_woeid")
    if args:
        woeid = args
    try:
        trends = twitter.get_trends(woeid)
    except TwitterError as error:
        print_error("Failed getting trends: %s" % error)
        return wc.WEECHAT_RC_OK

    print_to_current("%s-------------------" % wc.color("magenta"))
    header = "%sTrending " % wc.color("*cyan")
    if trends[0] != "Worldwide":
        header += "in "
    header += trends[0]
    print_to_current(header)
    for trend in trends[1:]:
        print_to_current(trend)
    print_to_current("%s-------------------" % wc.color("magenta"))
    return wc.WEECHAT_RC_OK

def search_cb(data, buffer, args):
    """The command to use for realtime search."""
    timelined = data
    setup_timeline(timelined, search=args)
    return wc.WEECHAT_RC_OK


def timelined_cb(data, command, rc, stdout, stderr):
    """Very generic callback in case timelined acts weird."""
    global buffers
    buf = buffers[data]
    name = wc.buffer_get_string(buf, "name")
    stream = data + "STREAM"
    del(hooks[stream])
    wc.buffer_close(buf)
    print_error("timelined for %s exited:" % name)
    print_error(stdout)
    print_error(stderr)
    return wc.WEECHAT_RC_OK

def timeline_prompt_cb(data, signal, signal_data):
    """Tweets from the timeline buffer, also shows how long your tweet is."""
    global buffers
    if  wc.current_buffer() != buffers['__TIMELINE']:
        return wc.WEECHAT_RC_OK
    wc.bar_item_update('tweet_counter')
    return wc.WEECHAT_RC_OK

def tcounter_item_cb(data, item, window):
    """Shows a counter of the current tweet length."""
    global buffers
    global twitter
    if wc.current_buffer() != buffers['__TIMELINE']:
        return ""
    buf_text = wc.buffer_get_string(buffers['__TIMELINE'], 'input')
    if buf_text.startswith("/"):
        return "0/140"
    count = twitter.status_count(buf_text)
    color = wc.color("default")
    if count > 140:
        color = wc.color("*red")
    return "%s%s/140" % (color, count)

def stop_timelined(prefix, buffer):
    """Unhooks the specified timeline hook."""
    global hooks
    global tlid
    # We have two hooks to unhook per window.
    stream = prefix + "STREAM"
    display = prefix + "DISPLAY"
    if stream in hooks:
        wc.unhook(hooks[stream])

    wc.unhook(hooks[display])

    # Kill timelined
    storage_dir = wc.config_get_plugin("storage_dir")
    pidfile = os.path.join(storage_dir, tlid[prefix] + ".pid")
    if os.path.exists(pidfile) and os.path.isfile(pidfile):
        with file(pidfile) as f:
            kill_process(int(f.read().rstrip()))
    # Remove the pidfile.
    os.unlink(pidfile)
    return wc.WEECHAT_RC_OK

def setup_timeline(timelined, followed=False, search=False):
    """Sets up the main timeline window."""
    global hooks
    global user
    global tlid
    global buffers
    if not search:
        name = "timeline"
        short_name = "twitter"
        title = "%s's timeline" % user.screen_name
        prefix = "__TIMELINE"
        search = False
        buf_cb = "tweet_cb"
    else:
        name = search
        short_name = search
        title = "Twitter search for %s" % search
        prefix = md5(search).hexdigest()
        buf_cb = "tweet_cb"
    buf = wc.buffer_new(name, buf_cb, "", "stop_timelined", prefix)
    # Some naming
    wc.buffer_set(buf, "title", title)
    wc.buffer_set(buf, "short_name", short_name)

    # We want mentions to highlight.
    wc.buffer_set(buf, "highlight_words", user.screen_name)

    if followed:
        # We want a nicklist to hold everyone we follow.
        wc.buffer_set(buf, "nicklist", "1")
        add_to_nicklist(buf, user.screen_name)

        for screen_name in followed:
            add_to_nicklist(buf, screen_name)

    storage_dir = wc.config_get_plugin("storage_dir")
    command = timelined + " " + storage_dir
    if search:
        command += " '%s'" % search
    timelinestream_hook = wc.hook_process(
        command,
        0, "timelined_cb", prefix)

    strkey = prefix + "STREAM"
    hooks[strkey] = timelinestream_hook

    # Check if there are new timeline entries every second.
    timelinedisplay_hook = wc.hook_timer(1 * 1000, 60, 0, "display_cb",
        prefix)
    diskey = prefix + "DISPLAY"
    hooks[diskey] = timelinedisplay_hook
    if search:
        wc.buffer_set(buf, "display", "1")
    buffers[prefix] = buf

    hooks['signal'] = wc.hook_signal("input_text_changed",
            "timeline_prompt_cb", "")

    if prefix is "__TIMELINE":
        tlid[prefix] = "timelined"
    else:
        tlid[prefix] = prefix

if wc.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, "shutdown_cb", ""):

    loaded = False

    # Default options
    default_storage = os.path.join(wc.info_get("weechat_dir", ''), "weetwit")
    script_options = {
            "storage_dir" : default_storage,
            "consumer_key" : "",
            "consumer_secret" : "",
            "access_token" : "",
            "access_token_secret" : "",
            "show_in_current" : "false",
            "current_while_away": "true",
            "current_while_detached": "true",
            "current_color" : "cyan",
            "timelined_location" : "timelined",
            "trend_woeid" : "1",
            "hash_color" : "red",
            "rt_style" : "postfix",
            "expand_urls" : "true",
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
        user = twitter.api.me()

        # Find timelined
        timelined = which(wc.config_get_plugin("timelined_location"))
        if not timelined:
            print_error(
                "Couldn't find timelined, please set 'plugins.var.python.weetwit.timelined"
            )

        tl = timelined[0]

        setup_timeline(tl, followed=followed)
        bar_item = wc.bar_item_new('tweet_counter', 'tcounter_item_cb', '')


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

        hook = wc.hook_command("tconversation",
                "Show the conversation leading up to a specific tweet.",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "conversation_cb", "")

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

        hook = wc.hook_command("tsearch", "Search twitter for something.",
            "search terms",
            "The terms to search for.",
            "",
            "search_cb", tl)

        hook = wc.hook_command("travail", "Show available trend areas.",
            "",
            "",
            "",
            "trends_available_cb", "")

        hook = wc.hook_command("trending", "Show what's trending.",
            "woeid",
            "The woeid of the trending area, if absent, uses the configured one.",
            "",
            "trends_cb", "")

        hook = wc.hook_command("treport", "Report a user for spam.",
            "[--yes] username",
            "Report a user for spam.",
            "",
            "report_spam_cb", "")

        hook = wc.hook_command("tfavourites", "Show your favourites",
            "",
            "Show your favourites",
            "",
            "show_favorites_cb", "")

        hook = wc.hook_command("tfavourite", "Add a tweet to your favourites.",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "tweet_favorite_cb", "")

        hook = wc.hook_command("tunfavourite",
            "Remove a tweet from your favourites.",
            "[tweet id/@username]",
            "The ID of the tweet, if @username is given, the ID of their last tweet is used.",
            "",
            "tweet_unfavorite_cb", "")
