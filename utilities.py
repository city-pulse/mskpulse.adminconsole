#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole: utilities

def get_menu(active = 'monitoring'):
	menu = [
		{'name':'Monitoring', 'link':'../', 'icon':'dashboard', 'active':int(active=='monitoring')},
		{'name':'Events', 'link':'../events', 'icon':'flash', 'active':int(active=='events')},
	]
	return menu