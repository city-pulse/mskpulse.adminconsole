# -*- coding: utf-8 -*-
from slackclient import SlackClient
from settings import REDIS_HOST, REDIS_PORT, REDIS_DB, SLACK_TOKEN
from time import sleep
from utilities import exec_mysql, get_mysql_con
from redis import StrictRedis

"""
# Bot user: U0LPX4E05
# Me: U0LQ0H3UG
[{u'type': u'presence_change', u'user': u'U0LPX4E05', u'presence': u'active'}]
[{u'type': u'user_typing', u'user': u'U0LQ0H3UG', u'channel': u'D0LPX4E21'}]
[{u'text': u'This is personal message to you', u'ts': u'1455110541.000002', u'user': u'U0LQ0H3UG', u'team': u'T0LPZMP55', u'type': u'message', u'channel': u'D0LPX4E21'}]
[{u'text': u'This is message in random channel', u'ts': u'1455110559.000007', u'user': u'U0LQ0H3UG', u'team': u'T0LPZMP55', u'type': u'message', u'channel': u'C0LPWCSLV'}]
[{u'text': u'Message in newsroom', u'ts': u'1455110589.000002', u'user': u'U0LQ0H3UG', u'team': u'T0LPZMP55', u'type': u'message', u'channel': u'C0LQ4S7SR'}]
[{u'event_ts': u'1455110617.070971', u'ts': u'1455110617.000003', u'subtype': u'message_deleted', u'hidden': True, u'deleted_ts': u'1455110589.000002', u'type': u'message', u'channel': u'C0LQ4S7SR', u'previous_message': {u'text': u'Message in newsroom', u'type': u'message', u'user': u'U0LQ0H3UG', u'ts': u'1455110589.000002'}}]

{u'text': u'<@U0LPX4E05>: show eventlist for today', u'ts': u'1455112532.000005', u'user': u'U0LQ0H3UG', u'team': u'T0LPZMP55', u'type': u'message', u'channel': u'C0LQ4S7SR'} 
<@U0LPX4E05>: show eventlist for today
{u'text': u'<!channel>:', u'ts': u'1455112545.000006', u'user': u'U0LQ0H3UG', u'team': u'T0LPZMP55', u'type': u'message', u'channel': u'C0LQ4S7SR'} 
<!channel>:

"""


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
		if event['type'] != 'message' or 'subtype' in event.keys() or event['channel'] != 'C0LQ4S7SR':
			return
		if event['text'].startswith('<@U0LPX4E05>'):
			message = [x.strip() for x in event['text'].split(' ')]
			if message[1] == 'help':
				reply = self.get_help(message[2:])
				return self.add_usermention(event['user'], reply)
			elif message[1] == 'show':
				reply = self.get_data_to_show(message[2:])
				return self.add_usermention(event['user'], reply)
			elif message[1] == 'update':
				return self.execute_update(message[2:])
			else:
				reply = self.add_usermention(event['user'], 'Unknown command, use "@editor help" for full commands list.')
				return reply

	def add_usermention(self, userid, text):
		"""
		Simple method for adding nickname of questionarie before answering.
		"""
		return '''<@{}>: {}'''.format(userid, text)

	def get_help(self, tokens):
		"""

		"""
		return "Currently working commands:\n- *show*\n- *update*\n- *help*\nSooner here will be overall help and help for different commands from docstrings."

	def get_data_to_show(self, tokens):
		"""

		"""
		if tokens[0] == 'eventlist':
			pass
		elif tokens[0] == 'event':
			pass
		elif tokens[0] == 'statistics':
			pass
		else:
			return 'Unknown object to show. Use "@editor help show" for more info.'

	def execute_update(self, tokens):
		return "Currently updates are not executed."

class SlackEvent(object):
	"""
	Event representation for Slack Bot:
	both short and long.
	"""
	def __init__(self, id, start, end, description, dump):
		self.id = id
		self.start = start
		self.end = end
		self.description = description
		self.duration = self.end - self.start
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

if __name__ == '__main__':
	bot =  EditorBot(SLACK_TOKEN)
	bot.run()