#!/usr/bin/env python3

# The board in use
from boards.enviroplus import EnviroPlus
enviroPlus = EnviroPlus();

# Threading
import threading

updateLock = threading.Lock()
updateThread = threading.Thread()

## Rest API
import flask
from flask import Flask,request, jsonify, Response

def createRestApp():
	app = Flask(__name__)

	def interrupt():
		global updateThread
		updateThread.cancel()

	def update():
		global updateThread
		with updateLock:
			enviroPlus.updateValues()

		updateThread = threading.Timer(1, update, ())
		updateThread.start()

	def startUpdateThread():

		# Preinit
		global updateThread

		# Update Thread
		updateThread = threading.Timer(1, update, ())

		# Thread Started
		updateThread.start()

	# Default path
	@app.route('/', methods=['GET'])
	def home():
		# A simple redirect to the values page
		return '''<meta http-equiv=\"refresh\" content=\"time=0; URL=/values" \/>'''

	# Our Values Path
	@app.route('/values', methods=['GET'])
	def api_all():
		with updateLock:

			# Response is the sensor values wrapped in json
			return Response(response=enviroPlus.getJSONValues(), status=200, mimetype="application/json")

	startUpdateThread()

	app.run(host="0.0.0.0", port="8080")

	return app

# create the rest app
app = createRestApp()