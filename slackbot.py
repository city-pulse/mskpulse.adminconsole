# -*- coding: utf-8 -*-
from slackclient import SlackClient
from settings import REDIS_HOST, REDIS_PORT, REDIS_DB, SLACK_TOKEN
from time import sleep
from datetime import datetime
from utilities import exec_mysql, get_mysql_con
from redis import StrictRedis
from msgpack import packb, unpackb
from json import dumps

class EditorBot(object):
	def __init__(self, token):
		self.socket = SlackClient(token)
		self.redis = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
		self.mysql = get_mysql_con()
		self.context = {
			'last_mentioned_event':None,
			'known_events':[],
		}

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
						self.socket.api_call('chat.postMessage', **reply)
				self.get_new_events()
				sleep(1)
		else:
			print "Connection failed"

	def get_new_events(self):
		events_to_pub = []
		for key in self.redis.keys("event:*"):
			if key[6:] in self.context['known_events']:
				continue
			event_data = self.redis.hgetall(key)
			if event_data['verification'] == '1' or (event_data['verification'] == 'NULL' and event_data['validity'] == '1'):
				event_data['start'] = datetime.strptime(event_data['start'], '%Y-%m-%d %H:%M:%S')
				event_data['end'] = datetime.strptime(event_data['end'], '%Y-%m-%d %H:%M:%S')
				event_data['validity'] = int(event_data['validity'])
				event = SlackEvent(start=event_data['start'], end=event_data['end'], validity=event_data['validity'], description=event_data['description'], dump=event_data['dumps'])
				events_to_pub.append(event.event_hash())
				self.context['known_events'].append(event.id)
				self.context['last_mentioned_event'] = event.id
				if len(self.context['known_events']) >= 200:
					self.context['known_events'].pop(0)
		if events_to_pub:
			self.socket.api_call('chat.postMessage', channel = 'C0LQ4S7SR', as_user = True, text = '<!channel>!!! ALARM!!! New event(s)!!!', attachments = dumps(events_to_pub))

	def prepare_reply(self, event):
		"""
		Method for preparing reply: it checks, if message was published in newsroom channel,
		if it starts with editorbot nickname, and if it has known command to execute.
		"""
		if 'type' not in event.keys() or event['type'] != 'message' or 'subtype' in event.keys() or event['channel'] != 'C0LQ4S7SR':
			return
		if event['text'].startswith('<@U0LPX4E05>'):
			message = [x.strip() for x in event['text'].split(' ')]
			reply = {'channel': event['channel'], 'as_user': True}
			if message[1] == 'help':
				reply['text'] = self.add_usermention(event['user'], self.get_help(message[2:]))
			elif message[1] == 'show':
				reply.update(self.get_data_to_show(message[2:]))
				if 'text' in reply:
					reply['text'] = self.add_usermention(event['user'], reply['text'])
			elif message[1] == 'update':
				reply['text'] = self.add_usermention(event['user'], self.execute_update(message[2:]))
			elif message[1] == 'ping':
				reply['text'] = self.add_usermention(event['user'], 'pong!')
			else:
				reply['text'] = self.add_usermention(event['user'], 'Unknown command, use "@editor help" for full commands list.')
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
			return "I will try to help you. Supported commands:\n- *show* - demonstrate collected and aggregated data;\n- *update* - change some data in the database;\n- *ping* - check, if I'm alive.\n- *help* - get this help note.\nTo get help on exact command type \"@editor help [command]\"."
		elif tokens[0] == 'show':
			return 'here you are:\n'+self.get_data_to_show.__doc__
		elif tokens[0] == 'update':
			return 'here you are:\n'+self.execute_update.__doc__
		elif tokens[0] == 'help':
			return 'Help on help? Srsly? What are you expecting?'
		elif tokens[0] == 'ping':
			return 'Simple command to check my availability.'
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
			return {'text':'This method is not yet implemented.'}
		elif tokens[0] == 'event':
			if len(tokens) == 1:
				return {'text': 'Specify event id to show.'}
			else:
				return self.get_event(tokens[1:])
		elif tokens[0] == 'statistics':
			return {'text':'This method is not yet implemented.'}
		else:
			return {'text':'Unknown object to show. Use "@editor help show" for more info.'}

	def execute_update(self, tokens):
		"""
		*Command: "@editor update ..."*
		This command is used to update some data on events in the database. Can be used to verify events, change description.
		"""
		return "Currently updates are not executed."

	def get_event(self, tokens):
		"""
		Method to look event by id (TBD: part of id) in the SQL and Redis DB's, and return it's full string representation.
		"""
		event_id = tokens[0]
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
				return {'text':'I don\'t know event with such id. :('}
		event = SlackEvent(start=event_dict['start'], end=event_dict['end'], validity=event_dict['validity'], description=event_dict['description'], dump=event_dict['dumps'])
		self.context['last_mentioned_event'] = event.id
		if len(tokens) == 1 or tokens[1] == 'short':
			attachments = [event.event_hash()]
		elif tokens[1] == 'top':
			try:
				num = int(tokens[2])
			except:
				num = 5
			attachments = [event.event_hash()] + event.messages_hash(n=num)
		elif tokens[1] == 'full':
			attachments = [event.event_hash()] + event.messages_hash(n=1000)
		else:
			attachments = [event.event_hash()]
		return {'text':'here you are:', 'attachments': dumps(attachments)}

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
		elif self.verification:
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
		for msg in e_dict['messages']:
			if 'media' in msg:
				e_dict['thumbnail'] = msg['media']
				break
		return e_dict

	def messages_representation(self):
		msgs = []
		nets = {1:'Twitter', 2:'Instagram', 3:'VKontakte'}
		messages = sorted(self.messages.values(), key = lambda x:x['token_score'], reverse=True)
		for item in messages:
			if item['token_score'] > 0:
				e = {'text':item['text'], 'network':nets[item['network']], 'time': item['tstamp'].strftime('%d %b %H:%M')}
				if 'media' in item.keys():
					e['media'] = item['media']
				msgs.append(e)
		return msgs

	def event_string(self):
		e_dict = self.event_representation()
		e_str = 'Event #{}\nDuration: {} ({} - {})\nMessages: {}\nStatus: {}'.format(e_dict['id'], self.duration_representation(), e_dict['start'], e_dict['end'], len(e_dict['messages']), e_dict['status'])
		return e_str

	def event_hash(self):
		e_dict = self.event_representation()
		if e_dict['status'] == 'confirmed real':
			color = '#98D1CB'
		elif e_dict['status'] == 'confirmed fake':
			color = '#F08159'
		elif e_dict['status'] == 'unconfirmed real':
			color = '#006D5C'
		elif e_dict['status'] == 'unconfirmed fake':
			color = '#EC6839'
		else:
			color = '#FF0000'

		e_hash = {
			'fallback':self.event_string(),
			'color': color,
			'title': 'Event #{}'.format(self.id),
			'text': self.description,
			'fields':[
				{'title':'Status', 'value':e_dict['status'], 'short':True},
				{'title':'Messages', 'value':len(e_dict['messages']), 'short':True},
				{'title':'Duration', 'value':self.duration_representation(), 'short':True}
			],
			}
		if 'thumbnail' in e_dict:
			e_hash['thumb_url'] = e_dict['thumbnail']
		return e_hash

	def messages_hash(self, n=5):
		msgs = []
		m_list = self.messages_representation()
		if len(m_list) < n:
			n = len(m_list)
		for i in range(n):
			m_hash = {
				'fallback':m_list[i]['text'],
				'color': '#666666',
				'text': m_list[i]['text'],
				'fields':[
					{'title':'Network', 'value':m_list[i]['network'], 'short':True},
					{'title':'Pubtime', 'value':m_list[i]['time'], 'short':True}
				]
			}
			if 'media' in m_list[i]:
				m_hash['thumb_url'] = m_list[i]['media']
			msgs.append(m_hash)
		return msgs

	def duration_representation(self):
		val = int(self.duration.total_seconds())
		secs = val%60
		mins = val//60
		if not mins:
			return '{} seconds'.format(secs)
		hours = mins//60
		mins = mins%60
		if not hours:
			return '{} min {} sec'.format(mins, secs)
		days = hours//24
		hours = hours%24
		if not days:
			return '{} h {} min'.format(hours, mins)
		return '{} d {} hours'.format(days, hours)

if __name__ == '__main__':
	bot =  EditorBot(SLACK_TOKEN)
	bot.run()