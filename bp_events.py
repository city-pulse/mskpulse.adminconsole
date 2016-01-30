#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole: events blueprint

from flask import Blueprint, render_template, redirect, url_for
from utilities import get_menu, mysql
from settings import REDIS_HOST, REDIS_PORT, REDIS_DB
from redis import StrictRedis
from datetime import datetime
from pickle import loads

event_page = Blueprint("event_page", __name__, template_folder="templates", static_folder="static")

@event_page.route("/")
def event_list():
	events = []

	# Redis part of events
	redis = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
	for key in redis.keys("event:*"):
		try:
			event = redis.hgetall(key)
		except TypeError:
			pass
		else:
			if event['verification'] == '1' or (event['verification'] == 'NULL' and event['validity'] == '1'):
				start = datetime.strptime(event['start'], '%Y-%m-%d %H:%M:%S')
				end = datetime.strptime(event['end'], '%Y-%m-%d %H:%M:%S')
				events.append({'id':key[6:], 'start':start, 'duration':end-start, 'messages':event['msgs'], 'description':event['description'].decode('utf-8')})
				if event['verification'] == '1':
					events[-1]['status'] = 'real'
				else:
					events[-1]['status'] = 'presumptive'
	if len(events) < 20:
		cursor = mysql.connection.cursor()
		cursor.execute('''SELECT id, start, end, msgs, description, verification, validity FROM events WHERE verification=1 OR (verification IS NULL AND validity = 1) ORDER BY start DESC LIMIT %s;''', (20 - len(events), ))
		e_data = cursor.fetchall()
		for item in e_data:
			events.append({'id':item[0], 'start':item[1], 'duration':item[2]-item[1], 'messages':item[3], 'description':item[4]})
			if item[5] == 1:
				events[-1]['status'] = 'real'
			else:
				events[-1]['status'] = 'presumptive'
	events = sorted(events, key=lambda x:x['start'], reverse=True)
	return render_template("events.html", navigation = get_menu("events"), events = events)

@event_page.route("/<id>")
def single_event(id):
	# look for key in Redis:
	redis = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
	if redis.keys("event:{}".format(id)):
		event_dict = redis.hgetall("event:{}".format(id))
		event = LightEvent(id=id, start = datetime.strptime(event_dict['start'], '%Y-%m-%d %H:%M:%S'), end = datetime.strptime(event_dict['end'], '%Y-%m-%d %H:%M:%S'), description = event_dict['description'].decode('utf-8'), dump=event_dict['dumps'])
	else:
		cursor = mysql.connection.cursor()
		cursor.execute('''SELECT start, end, description, dumps FROM events WHERE id = %s;''', (id, ))
		event_data = cursor.fetchall()[0]
		event = LightEvent(id=id, start=event_data[0], end=event_data[1], description=event_data[2], dump=event_data[3])

	return render_template("event.html", navigation = get_menu("events"), data = event.event_representation())

class LightEvent(object):
	def __init__(self, id, start, end, description, dump):
		self.id = id
		self.start = start
		self.end = end
		self.description = description
		self.duration = self.end - self.start
		self.cursor = mysql.connection.cursor()
		self.load_dump(dump)

	def load_dump(self, dump):
		event_data = loads(dump)
		self.messages = event_data['messages']
		if 'compressed' not in event_data.keys() or not event_data['compressed']:
			for item in event_data['media'].values():
				self.messages[item['tweet_id']]['media'] = item['url']
		else:
			self.get_messages_data()
			self.get_media_data()
		self.created = event_data['created']
		self.updated = event_data['updated']
		if 'verification' in event_data.keys():
			self.verification = event_data['verification']
		if 'validation' in event_data.keys():
			self.validation = event_data['validation']
		if 'cores' in event_data.keys():
			self.cores = event_data['cores']

	def get_messages_data(self):
		self.cursor.execute('''SELECT * FROM tweets WHERE id in ({});'''.format(','.join(['"'+str(x)+'"' for x in self.messages.keys()])))
		data = self.cursor.fetchall()
		for item in data:
			self.messages[item[0]]['id'] = item[0]
			self.messages[item[0]]['text'] = item[1]
			self.messages[item[0]]['lat'] = item[2]
			self.messages[item[0]]['lng'] = item[3]
			self.messages[item[0]]['tstamp'] = item[4]
			self.messages[item[0]]['user'] = item[5]
			self.messages[item[0]]['network'] = item[6]
			self.messages[item[0]]['iscopy'] = item[7]

	def get_media_data(self):
		self.cursor.execute('''SELECT * FROM media WHERE tweet_id in ({});'''.format(','.join(['"'+str(x)+'"' for x in self.messages.keys()])))
		data = self.cursor.fetchall()
		for item in data:
			self.messages[item[1]]['media'] = item[2]

	def event_representation(self):
		if self.verification:
			status = 'real'
		else:
			status = 'presumptive'
		e_dict = {
			'start':self.start,
			'end':self.end,
			'created':self.created,
			'id':self.id,
			'description':self.description,
			'duration':self.duration,
			'status':status,
			'messages':self.messages_representation()
		}
		return e_dict

	def messages_representation(self):
		msgs = []
		nets = {1:'Twitter', 2:'Instagram', 3:'VKontakte'}
		messages = sorted(self.messages.values(), key = lambda x:x['token_score'], reverse=True)
		for item in messages:
			if item['token_score'] > 0:
				e = {'text':item['text'], 'network':nets[item['network']], 'time':item['tstamp']}
				if 'media' in item.keys():
					e['media'] = item['media']
				else:
					e['media'] = 'http://www.designofsignage.com/application/symbol/building/image/600x600/no-photo.jpg'
				msgs.append(e)
		return msgs

