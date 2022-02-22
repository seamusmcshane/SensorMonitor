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

# Enviroplus Board support
# Devices supported		-	Temperature, Humidity and Pressure, Lux, Proximity, Gas and LCD.
# Devices not supported	-	Noise and Particulate matter addon.

# Temperature, Humidity and Pressure
from smbus import SMBus
from sensors.BME280 import BME280
from subprocess import PIPE, Popen

# The Lux/Proximity sensors
from ltr559 import LTR559


# Gas sensor
from sensors import MICS6814

# math
import math

# EnviroPlus OLED Display
from boards.enviroplusdisplay import Display


# Assuming updating at 1 sample per second this is ten seconds of samples
SAMPLE_WINDOW_LEN = 10;


# A class to describe what our json returned values will look like
import json
class Values:

	proximity = 0.0
	lux = 0.0
	temperature = 0.0
	humidity = 0.0
	pressure = 0.0
	reducing = 0.0
	oxidising = 0.0
	nh3 = 0.0

	def __init__(self):
		self.proximity = 0.0
		self.lux = 0.0
		self.temperature = 0.0
		self.humidity = 0.0
		self.pressure = 0.0
		self.reducing = 0.0
		self.oxidising = 0.0
		self.nh3 = 0.0

	def toJSON(self):
		return "{ \"values\" :" + json.dumps(self, default=lambda o: o.__dict__, sort_keys=False) + "}"

# The board class
class EnviroPlus:

	# frame count, we start on 1 as this is the first update
	frame=1;

	# startup display mode at startup
	lcd_mode=LCD_MODE.SENSORS;

	# LCD
	lcd=0;
	fb=0;

	# THS
	bme280=0;

	bme280_raw_temps = [];						# to account for noise influence on sensor readings
	bme280_raw_humidity_window = [];			# to account for noise influence on sensor readings
	bme280_raw_pressure_window  = [];			# to account for noise influence on sensor readings

	cpu_temps = [];								# to account for cpu temp influence on sensor readings

	smooth_size = SAMPLE_WINDOW_LEN;			# Depends on how often you sample. Compensation against a PI CPU burst heating up the sensor.

	# This you will need to calibrate this as they depend on the PI. Best done with a physical thermometer or a calibrated reference sensor.
	smooth_factor = 0.9;						# Depends on how close the sensor is to the PI, and the Pi's thermals. Here there is a tall header so 1cm distance and pi is inside a aluminum case, with very low load.

	# LUX
	ltr559=0;

	ltr559_avg_window = SAMPLE_WINDOW_LEN		# size of the avg window
	ltr559_raw_proximity_window = [];			# to account for noise influence on sensor readings
	ltr559_raw_lux_window = [];					# to account for noise influence on sensor readings


	# Gas
	mics6814=0;

	mics6814_avg_window = SAMPLE_WINDOW_LEN		# size of the avg window
	mics6814_raw_reducing_window = [];			# to account for noise influence on sensor readings
	mics6814_raw_oxidising_window = [];			# to account for noise influence on sensor readings
	mics6814_raw_nh3_window = [];				# to account for noise influence on sensor readings

	# Particulate mater addon need HW to test
	# pms5003=0;

	# Sensor values for formating into json
	currentValues = Values()

	# Setup the LCD controller and backing frame buffer
	def initDisplay(self):

		self.display = Display()

		print("OLED Display Ready")

	# Setup the BME Temperature, Humidity and Pressure sensor
	def initBME280(self):

		# Create a BME280 instance (SMBus 1)
		self.bme280 = BME280(i2c_dev=SMBus(1))

		self.bme280.setup(mode="forced", temperature_oversampling=16, pressure_oversampling=16)

		print("BME280 Ready")

	# Setup the LTR559 Proximity and Light Sensor
	def initLTR559(self):

		self.ltr559 = LTR559()

		print("LTR559 Ready")

	# Setup the MICS6814 Analog Gas Sensor
	def initMICS6814(self):

		self.mics6814 = MICS6814

		# do a few readings to clear some of the initial startup noise
		# will not help if the sensor is cold starting
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()
		td = self.mics6814.read_all()

		print("MICS6814 Ready")

	# Initialises all the sub compoenents when an EnviroPlus object is created.
	def __init__(self):

		self.initBME280()
		self.initLTR559()
		self.initMICS6814();
		self.initDisplay()

		print("EnviroPlus Ready");

	# Fetches the current cpu temperature
	def get_cpu_temperature(self):

		process = Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=PIPE)
		(output, process) = process.communicate()
		#print ("output 1: ", output.strip())
		return float(output) * 0.001

	# This stores the raw value in a window and returns the current average of the window. Window limited to window len.
	def smooth_value_generic(self, raw_window, window_len, raw_value):

		# Add our new value to the end
		raw_window.append(raw_value)

		# If the length is greater than the max window size, remove the first sample
		if (len(raw_window) > window_len):
			del raw_window[0]

		# Return the new average of all samples in the window
		return sum(raw_window) / float(len(raw_window))

	# Assumes you are sampling the sensor more than you are storing the data
	def smooth_temp_value(self, window_len, raw_value):

		# Our raw cpu temp window
		ncpu_temp = self.get_cpu_temperature()
		self.cpu_temps.append(ncpu_temp)

		if (len(self.cpu_temps) > self.smooth_size):
			del self.cpu_temps[0]

		# Our raw temp window
		self.bme280_raw_temps.append(raw_value)

		if (len(self.bme280_raw_temps) > window_len):
			del self.bme280_raw_temps[0]

		# Our raw average temperator window average
		avg_temp = sum(self.bme280_raw_temps) / float(len(self.bme280_raw_temps))

		# Our average cpu temp window
		smoothed_cpu_temp = sum(self.cpu_temps) / float(len(self.cpu_temps))

		# Dampens the average temp by the cpu average temp.
		# Dampening is scaled using a smooth factor for fine tuning.
		# Adjust smooth_factor based on how close the sensor is to the cpu/case and how hot they get.
		# see smooth_factor at the top of this class.
		return (avg_temp - ((smoothed_cpu_temp - avg_temp) / self.smooth_factor))




	def updateValues(self):


		# ltr559
		proximity = self.ltr559.get_proximity()

		lux = self.ltr559.get_lux();
		lux = self.smooth_value_generic(self.ltr559_raw_lux_window, SAMPLE_WINDOW_LEN, lux)

		# BME280 lib is modified to coalesc the three calls
		thp = self.bme280.get_thp()
		temperature =  self.smooth_temp_value(SAMPLE_WINDOW_LEN, thp[0])	# calls temperature specifc smooth
		# LTR559
		r_proximity = self.ltr559.get_proximity()
		r_lux = self.ltr559.get_lux()

		humidity = self.smooth_value_generic(self.bme280_raw_humidity_window, SAMPLE_WINDOW_LEN, thp[1])

		pressure = self.smooth_value_generic(self.bme280_raw_pressure_window, SAMPLE_WINDOW_LEN, thp[2])

		# MICS6814
		gas_data = MICS6814.read_all()

		reducing = self.smooth_value_generic(self.mics6814_raw_reducing_window, SAMPLE_WINDOW_LEN, gas_data.reducing)

		oxidising = self.smooth_value_generic(self.mics6814_raw_oxidising_window, SAMPLE_WINDOW_LEN, gas_data.oxidising)

		nh3 = self.smooth_value_generic(self.mics6814_raw_nh3_window, SAMPLE_WINDOW_LEN, gas_data.nh3)


		# Send the values to the display
		self.display.updateValues(proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3)
		# Store our values (to turn into json later)
		self.currentValues.proximity, self.currentValues.lux, self.currentValues.temperature, self.currentValues.humidity, self.currentValues.pressure, self.currentValues.reducing, self.currentValues.oxidising, self.currentValues.nh3 = proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3

		# update the display - note raw proximity value needed here
		self.display.draw(r_proximity)
		# return the sensor values when called (for debugging)
		return proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3

	def getJSONValues(self):
		# Return values formated as json
		return self.currentValues.toJSON()