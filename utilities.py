#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole: utilities

from flask.ext.mysqldb import MySQL
mysql = MySQL()

def get_menu(active = 'monitoring'):
	menu = [
		{'name':'Monitoring', 'link':'../', 'icon':'dashboard', 'active':int(active=='monitoring')},
		{'name':'Events', 'link':'../events', 'icon':'flash', 'active':int(active=='events')},
	]
	return menu