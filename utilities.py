#!/usr/bin/python
# -*- coding: utf-8 -*-
# MSK.Pulse adminconsole: utilities

#from flask.ext.mysqldb import MySQL
#mysql = MySQL()

def get_menu(active = 'monitoring'):
	menu = [
		{'name':'Monitoring', 'link':'../', 'icon':'dashboard', 'active':int(active=='monitoring')},
		{'name':'Events', 'link':'../events', 'icon':'flash', 'active':int(active=='events')},
	]
	return menu

def exec_mysql(cmd, connection):
	"""
	Unified function for MySQL interaction from multiple sources and threads.

	Args:
		cmd (str): command, to be executed.
		connection (PySQLPool.PySQLConnection): connection to the database object.
	"""
	from PySQLPool import getNewQuery
	query = getNewQuery(connection, commitOnEnd=True)
	result = query.Query(cmd)
	return query.record, result

def get_mysql_con():
	"""
	Function for creating PySQLPool.PySQLConnection object from settings parameters.
	Additionaly sets up names, and connection charset to utf8mb4.
	"""
	from PySQLPool import getNewPool, getNewConnection, getNewQuery
	from settings import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB
	getNewPool().maxActiveConnections = 1
	mysql_db = getNewConnection(username=MYSQL_USER, password=MYSQL_PASSWORD, host=MYSQL_HOST, db=MYSQL_DB)
	query = getNewQuery(mysql_db, commitOnEnd=True)
	query.Query('SET NAMES utf8mb4;')
	query.Query('SET CHARACTER SET utf8mb4;')
	query.Query('SET character_set_connection=utf8mb4;')
	return mysql_db