#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole: events blueprint

from flask import Blueprint, render_template
from utilities import get_menu

event_page = Blueprint("event_page", __name__, template_folder="templates", static_folder="static")

@event_page.route("/")
def show():
	return render_template("events.html", navigation = get_menu("events"))