#!/usr/bin/env python3

# The board in use
from boards.enviroplus import EnviroPlus
enviroPlus = EnviroPlus();

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