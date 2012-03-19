#!/usr/bin/env python
#coding: utf-8
#
# File Name: utils.py
#
# Description: Collection of helper functions.
#
# Creation Date: 2012-03-02
#
# Last Modified: 2012-03-14 10:33
#
# Created By: Daniël Franke <daniel@ams-sec.org>
#

import htmlentitydefs
import re
import os

import logging


##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    "Removes HTML or XML character references and entities from a text string."
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    if not text:
        return "None"
    return re.sub("&#?\w+;", fixup, text)


def kill_process(pid):
    """Kills pid in no matter what."""
    logging.getLogger('timelined').addHandler(logging.NullHandler())
    try:
        os.kill(pid, 0)
    except OSError:
        logging.info("Process wasn't running.")
        return True

    os.kill(pid, 15)

    try:
       os.kill(pid, 0)
    except OSError:
       logging.info("Process cleanly killed")
       return True

    os.kill(pid, 9)

    try:
        os.kill(pid, 0)
    except OSError:
        logging.info("Process forcefully killed.")
        raise Exception("Zombie alert!")

# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
def which(name, flags=os.X_OK):
    """Search PATH for executable files with the given name.
    
    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.
    
    @type name: C{str}
    @param name: The name for which to search.
    
    @type flags: C{int}
    @param flags: Arguments to L{os.access}.
    
    @rtype: C{list}
    @param: A list of the full paths to files found, in the
    order in which they were found.
    """
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result

