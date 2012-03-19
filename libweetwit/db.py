#!/usr/bin/env python
#coding: utf-8
#
# File Name: twhelpers.py
#
# Description: Database class for weetwit.
#
# Creation Date: 2012-01-13
#
# Last Modified: 2012-03-14 22:00
#
# Created By: Daniël Franke <daniel@ams-sec.org>

import sqlite3


class DB(object):
    def __init__(self, storage_dir):
        """Returns a connection to the sqlite db."""
        self.dbfile = "%s/database" % storage_dir
        self.conn = sqlite3.connect(self.dbfile)
        self.cursor = self.conn.cursor()
        self.connect()
        try:
            if not self.__initialised():
                self.__init_db()
        finally:
            self.conn.commit()

    def connect(self):
        """Connects to the db."""
        self.conn = sqlite3.connect(self.dbfile)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        """Closes the connection."""
        self.cursor.close()
        self.conn.close()

    def set_config(self, option, value):
        """Sets a configuration option in the database."""
        try:
            self.cursor.execute("select option from config where option = ?",
                    (option,))
            if len(self.cursor.fetchall()) > 0:
                self.cursor.execute(
                    "update config set value = ? where option = ?", (value,
                            option))
            else:
                self.cursor.execute(
                    "insert into config (option, value) values (?,?)",
                    (option, value))
        finally:
            self.conn.commit()
        return True

    def get_config(self, option):
        """Gets a configuration option in the database."""
        value = False
        try:
            self.cursor.execute("select value from config where option = ?",
                    (option,))
            rows = self.cursor.fetchall()

            if len(rows) == 1:
                value = rows[0][0]
        finally:
            self.conn.commit()

        return value

    def get_last_tid(self, screen_name):
        """Returns the last cached tid for @screen_name from the SQLite db."""
        tid = False
        try:
            self.cursor.execute("select id from cached_ids where screen_name = ?",
                (screen_name,))
            rows = self.cursor.fetchall()
            if len(rows) == 1:
                tid = rows[0][0]
        finally:
            self.conn.commit()
        return tid

    def set_last_tid(self, screen_name, tid):
        """Caches the last tid for @screen_name."""
        try:
            self.cursor.execute("select id from cached_ids where screen_name = ?",
                    (screen_name,))
            if len(self.cursor.fetchall()) > 0:
                self.cursor.execute(
                    "update cached_ids set id = ? where screen_name = ?", 
                    (tid, screen_name))
            else:
                self.cursor.execute(
                    "insert into cached_ids (id, screen_name) values (?, ?)",
                    (tid, screen_name))
        finally:
            self.conn.commit()
        return True



    def __initialised(self):
        """Checks if all tables we need exist."""
        self.cursor.execute(
            """select * from sqlite_master where name IN
            ('statuses', 'config', 'cached_ids')"""
        )
        if len(self.cursor.fetchall()) != 3:
            return False
        return True

    def __init_db(self):
        """Initialises the database."""
        # Try to drop all tables in case of an incomplete install.
        try:
            self.cursor.execute('''drop table statuses''')
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute('''drop table config''')
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute('''drop table cached_ids''')
        except sqlite3.OperationalError:
            pass

        self.cursor.execute('''
            create table statuses
                (id bigint NOT NULL PRIMARY KEY, screen_name text NOT NULL,
                stext text NOT NULL, created DATETIME NOT NULL)'''
        )
        self.cursor.execute('''
            create table config
                (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                option text NOT NULL UNIQUE,
                value text)'''
        )
        self.cursor.execute('''
            create table cached_ids
                (id bigint NOT NULL PRIMARY KEY,
                screen_name text NOT NULL UNIQUE
            )'''
        )
        return True

