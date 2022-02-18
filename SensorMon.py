#!/usr/bin/env python3
#
# Seamus McShane 2022
#
# This file is part of SensorMonitor.
#
# SensorMonitor is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version 3
# as published by the Free Software Foundation.
#
# SensorMonitor is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License Version 3 for more details.
#

# Commandline Arguments
from argparse import ArgumentParser
parser = ArgumentParser(description='Sensor Monitor')

# Sets the name of the boardname to load
parser.add_argument('-boardname', help='A sensor board name.')

# Sets boardlist to true when supplied
parser.add_argument('-boardlist', '-bl', help='Prints the list of supported boards.', action='store_true')

# Read the args
args = parser.parse_args()

# Display the board list
boardList = args.boardlist
if boardList:
	print("\t\tBoard Support List")
	print("Board Name\t\tDescription")
	print("_______________________________________________________________")
	print("EnviroPlus\t\tPimoroni EnviroPlus")
	print("WaveshareESH\t\tWaveshare Enviroment Sensor HAT")
	exit()

# Load the choosen board or exit
boardName = args.boardname
if boardName != None:
	print("Choosen Board " + boardName)
else:
	print("No Board Choosen, showing help")
	parser.print_help()
	exit()

# The board module importer
import importlib
BoardClass = getattr(importlib.import_module("boards." + boardName.lower()), boardName)

# Instantiate the selected board
board = BoardClass()

# Threading
import threading

updateLock = threading.Lock()
updateThread = threading.Thread()
running = False

# Sleep
from time import sleep

## Rest API
import flask
from flask import Flask,request, jsonify, Response

def createRestApp():
	app = Flask(__name__)

	def update():
		global running
		global updateLock
		while running:
			with updateLock:
				board.updateValues()
			# Sleep outside the lock!
			sleep(1)

	def beginUpdating():
		global running
		global updateThread

		# Update Thread
		updateThread = threading.Thread(None, update)

		# Start
		running = True
		updateThread.start()

	# Default path
	@app.route('/', methods=['GET'])
	def home():
		# A simple redirect to the values page
		return '''<meta http-equiv=\"refresh\" content=\"time=0; URL=/values" \/>'''

	# Our Values Path
	@app.route('/values', methods=['GET'])
	def api_all():
		global updateLock
		with updateLock:
			# Response is the sensor values wrapped in json
			return Response(response=board.getJSONValues(), status=200, mimetype="application/json")

	beginUpdating()

	app.run(host="0.0.0.0", port="8080")

	return app

# create the rest app
app = createRestApp()