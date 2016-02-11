# -*- coding: utf-8 -*-
from slackclient import SlackClient
from settings import REDIS_HOST, REDIS_PORT, REDIS_DB, SLACK_TOKEN
from time import sleep
from datetime import datetime
from utilities import exec_mysql, get_mysql_con
from redis import StrictRedis
from msgpack import packb, unpackb

class EditorBot(object):
	def __init__(self, token):
		self.socket = SlackClient(token)
		self.redis = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
		self.mysql = get_mysql_con()

	def run(self):
		"""
		Infinity loop for SlackBot script: on every step it looks for new messages in allowed channels,
		reacts on them, and looks for new events in Redis database.
		"""
		if self.socket.rtm_connect():
			while True:
				event = self.socket.rtm_read()
				if event:
					reply = self.prepare_reply(event[0])
					if reply:
						self.socket.rtm_send_message(reply['channel'], reply['message'])
				sleep(1)
		else:
			print "Connection failed"

	def prepare_reply(self, event):
		"""
		Method for preparing reply: it checks, if message was published in newsroom channel,
		if it starts with editorbot nickname, and if it has known command to execute.
		"""
		if 'type' not in event.keys() or event['type'] != 'message' or 'subtype' in event.keys() or event['channel'] != 'C0LQ4S7SR':
			return
		if event['text'].startswith('<@U0LPX4E05>'):
			message = [x.strip() for x in event['text'].split(' ')]
			if message[1] == 'help':
				reply = self.get_help(message[2:])
			elif message[1] == 'show':
				reply = self.get_data_to_show(message[2:])
			elif message[1] == 'update':
				reply = self.execute_update(message[2:])
			else:
				reply = 'Unknown command, use "@editor help" for full commands list.'
			reply = {'message':self.add_usermention(event['user'], reply), 'channel':event['channel']}
			return reply

	def add_usermention(self, userid, text):
		"""
		Simple method for adding nickname of questionarie before answering.
		"""
		return '''<@{}>: {}'''.format(userid, text)

	def get_help(self, tokens):
		"""
		Method for formulating answer to help command.
		"""
		if not tokens:
			return "I will try to help you. Currently working commands:\n- *show* - demonstrate collected and aggregated data;\n- *update* - change some data in the database;\n- *help* - get this help note.\nTo get help on exact command type \"@editor help [command]\"."
		elif tokens[0] == 'show':
			return 'here you are:\n'+self.get_data_to_show.__doc__
		elif tokens[0] == 'update':
			return 'here you are:\n'+self.execute_update.__doc__
		else:
			return 'I don\'t know such command. Sorry, bro.'

	def get_data_to_show(self, tokens):
		"""
		*Command: "@editor show ..."*
		This command is used to show some data. There are several options to show:
		- eventlist [time interval] - show list of multiple events in a short form;
		- event [event id] - show full info about specific event;
		- statistics [time interval] - show database stats during specified period.
		"""
		if tokens[0] == 'eventlist':
			return 'This method is not yet implemented.'
		elif tokens[0] == 'event':
			return self.get_event(tokens[1])
		elif tokens[0] == 'statistics':
			return 'This method is not yet implemented.'
		else:
			return 'Unknown object to show. Use "@editor help show" for more info.'

	def execute_update(self, tokens):
		"""
		*Command: "@editor update ..."*
		This command is used to update some data on events in the database. Can be used to verify events, change description.
		"""
		return "Currently updates are not executed."

	def get_event(self, event_id):
		"""
		Method to look event by id (TBD: part of id) in the SQL and Redis DB's, and return it's full string representation.
		"""
		if self.redis.keys("event:{}".format(event_id)):
			event_dict = self.redis.hgetall("event:{}".format(event_id))
			event_dict['start'] = datetime.strptime(event_dict['start'], '%Y-%m-%d %H:%M:%S')
			event_dict['end'] = datetime.strptime(event_dict['end'], '%Y-%m-%d %H:%M:%S')
			event_dict['validity'] = int(event_dict['validity'])
		else:
			q = '''SELECT * FROM events WHERE id = '{}';'''.format(event_id)
			try:
				event_dict = exec_mysql(q, self.mysql)[0][0]
			except IndexError:
				return 'I don\'t know event with such id. :('
		event = SlackEvent(start=event_dict['start'], end=event_dict['end'], validity=event_dict['validity'], description=event_dict['description'], dump=event_dict['dumps'])
		return str(event.event_representation())

class SlackEvent(object):
	"""
	Event representation for Slack Bot:
	both short and long.
	"""
	def __init__(self, start, end, validity, description, dump):
		self.start = start
		self.end = end
		self.description = description
		self.duration = self.end - self.start
		self.validity = validity
		self.mysql = get_mysql_con()
		self.load_dump(dump)

	def load_dump(self, dump):
		event_data = unpackb(dump)
		self.id = event_data['id']
		self.created = datetime.fromtimestamp(event_data['created'])
		self.updated = datetime.fromtimestamp(event_data['updated'])
		self.verification = event_data['verification']
		self.messages = {x['id']:x for x in event_data['messages']}
		self.get_messages_data()
		self.get_media_data()

	def get_messages_data(self):
		q = '''SELECT * FROM tweets WHERE id in ({});'''.format(','.join(['"'+str(x)+'"' for x in self.messages.keys()]))
		data = exec_mysql(q, self.mysql)[0]
		for item in data:
			self.messages[item['id']].update(item)

	def get_media_data(self):
		q = '''SELECT * FROM media WHERE tweet_id in ({});'''.format(','.join(['"'+str(x)+'"' for x in self.messages.keys()]))
		data = exec_mysql(q, self.mysql)[0]
		for item in data:
			self.messages[item['tweet_id']]['media'] = item['url']

	def event_representation(self):
		if self.verification is None:
			if self.validity:
				status = 'unconfirmed real'
			else:
				status = 'unconfirmed fake'
		if self.verification:
			if self.validity:
				status = 'confirmed real'
			else:
				status = 'misdefined as fake'
		else:
			if self.validity:
				status = 'misdefined as real'
			else:
				status = 'confirmed fake'
		e_dict = {
			'start':self.start.strftime('%Y-%m-%d %H:%M:%S'),
			'end':self.end.strftime('%Y-%m-%d %H:%M:%S'),
			'created':self.created.strftime('%Y-%m-%d %H:%M:%S'),
			'updated':self.updated.strftime('%Y-%m-%d %H:%M:%S'),
			'id':self.id,
			'description':self.description,
			'duration':self.duration.total_seconds(),
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
				e = {'text':item['text'], 'network':nets[item['network']], 'time': item['tstamp'].strftime('%Y-%m-%d %H:%M:%S')}
				if 'media' in item.keys():
					e['media'] = item['media']
				msgs.append(e)
		return msgs

if __name__ == '__main__':
	bot =  EditorBot(SLACK_TOKEN)
	bot.run()