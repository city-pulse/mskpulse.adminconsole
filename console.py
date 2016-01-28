#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole main module

from flask import Flask, request, Response, render_template
from functools import wraps
from settings import CREDENTIALS
from md5 import new
from utilities import get_menu

# Blueprints
from bp_events import event_page

app = Flask(__name__)
app.register_blueprint(event_page, url_prefix='/events')

def check_auth(username, password):
	"""This function is called to check if a username /
	password combination is valid.
	"""
	if username in CREDENTIALS.keys():
		return CREDENTIALS[username]['pass_hash'] == new(password).hexdigest()
	return False

def authenticate():
	"""Sends a 401 response that enables basic auth"""
	return Response(
	'Could not verify your access level for that URL.\n'
	'You have to login with proper credentials', 401,
	{'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization
		if not auth or not check_auth(auth.username, auth.password):
			return authenticate()
		return f(*args, **kwargs)
	return decorated

@app.route("/")
@requires_auth
def mainpage():
	return render_template("index.html", navigation = get_menu('monitoring'))

if __name__ == "__main__":
	app.run(debug=True, port=5000, host = 'localhost')