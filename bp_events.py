#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole: events blueprint

from flask import Blueprint, render_template, redirect, url_for
from utilities import get_menu, mysql

event_page = Blueprint("event_page", __name__, template_folder="templates", static_folder="static")

@event_page.route("/")
def event_list():
	cursor = mysql.connection.cursor()
	cursor.execute('''SELECT id, start, msgs, verification FROM events ORDER BY start DESC LIMIT 20;''')
	e_data = cursor.fetchall()
	data = []
	for item in e_data:
		event = {'id':item[0], 'time':item[1], 'messages':item[2]}
		if item[3]:
			event['status'] = 'real'
		else:
			event['status'] = 'presumptive'
		data.append(event)
	return render_template("events.html", navigation = get_menu("events"), events = data)

@event_page.route("/<id>")
def single_event(id):
	cursor = mysql.connection.cursor()
	cursor.execute('''SELECT id, start, msgs, verification FROM events WHERE id = %s;''', (id, ))
	try:
		e_data = cursor.fetchall()[0]
	except IndexError:
		return redirect(url_for('.event_list'))
	data = {'id':e_data[0], 'time':e_data[1], 'messages':e_data[2]}
	if e_data[3]:
		data['status'] = 'real'
	else:
		data['status'] = 'presumptive'
	return render_template("event.html", navigation = get_menu("events"), data = data)