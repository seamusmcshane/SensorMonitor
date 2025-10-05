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

# EnviroPlus Board support
# Devices supported		-	Temperature, Humidity and Pressure, Lux, Proximity, Gas and LCD.
# Devices not supported	-	Noise and Particulate matter addon.

from smbus import SMBus
I2C_DEV=SMBus(1)

# Temperature, Humidity and Pressure
from sensors.BME280 import BME280

# CPU Temp
from subprocess import PIPE, Popen

# The Lux/Proximity sensors
from ltr559 import LTR559

# Gas sensor
from sensors import MICS6814

# EnviroPlus OLED Display
from boards.enviroplusdisplay import Display

from utility.cbuffer import CBuffer
from utility.picputemperature import PICPUTemp

# Assuming updating at 1 sample per second this is ten seconds of samples
SAMPLE_WINDOW_LEN = 10

# A class to describe what our JSON returned values will look like
import json
class Values:

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

	# Setup the LCD controller and backing frame buffer
	def initDisplay(self):

		self.display = Display()

		print("OLED Display Ready")

	# Setup the BME Temperature, Humidity and Pressure sensor
	def initBME280(self):

		# CPU Temp
		self.cpu_temp = PICPUTemp(SAMPLE_WINDOW_LEN)

		# Buffers for BME280 stats
		self.bme280_temps = CBuffer(SAMPLE_WINDOW_LEN)
		self.bme280_humidity = CBuffer(SAMPLE_WINDOW_LEN)
		self.bme280_pressure = CBuffer(SAMPLE_WINDOW_LEN)

		# Create a BME280 instance (SMBus 1)
		self.bme280 = BME280(i2c_dev=I2C_DEV)
		self.bme280.setup(mode="forced", temperature_oversampling=16, pressure_oversampling=16)

		print("BME280 Ready")

	# Setup the LTR559 Proximity and Light Sensor
	def initLTR559(self):

		# Buffers for the LTR559 Stats
		self.ltr559_lux = CBuffer(SAMPLE_WINDOW_LEN)
		self.ltr559_prox = CBuffer(SAMPLE_WINDOW_LEN)

		self.ltr559 = LTR559()

		print("LTR559 Ready")

	# Setup the MICS6814 Analog Gas Sensor
	def initMICS6814(self):

		# Buffers for the MICS6814 Stats
		self.mics6814_reducing = CBuffer(SAMPLE_WINDOW_LEN)
		self.mics6814_oxidising = CBuffer(SAMPLE_WINDOW_LEN)
		self.mics6814_nh3 = CBuffer(SAMPLE_WINDOW_LEN)

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

	# Initialises all the sub components when an EnviroPlus object is created.
	def __init__(self, smooth_factor = 0.9):

		# You will need to calibrate this.
		# Best done with a physical thermometer or a calibrated reference sensor.
		# Value depends on how close the sensor is to the PI, and the Pi's thermals.
		# 0.9 was used with a tall header outside a case with - 1cm distance to the PI.
		# PI is inside a aluminium case, with very low load.
		self.smooth_factor = smooth_factor

		# Sensor values for formatting into JSON
		self.currentValues = Values()

		self.initBME280()
		self.initLTR559()
		self.initMICS6814()
		self.initDisplay()

		print("EnviroPlus Ready")

	# Fetches the current cpu temperature
	def get_cpu_temperature(self):

		process = Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=PIPE)
		(output, process) = process.communicate()
		#print ("output 1: ", output.strip())
		return float(output) * 0.001

	def updateValues(self):
		""" Performs a collection of values from supported devices """

		# Update the cpu temp which is used to smooth/adjust the bme280 temp
		self.cpu_temp.update()

		# BME280 lib is modified to coalesce the three calls
		thp = self.bme280.get_thp()
		temperature = thp[0]
		self.bme280_humidity.addValue(thp[1])
		humidity = self.bme280_humidity.getValue()
		self.bme280_pressure.addValue(thp[2])
		pressure = self.bme280_pressure.getValue()

		# Write current smoothed data to JSON values
		self.currentValues.temperature, self.currentValues.humidity, self.currentValues.pressure = temperature, humidity, pressure

		# LTR559
		r_proximity = self.ltr559.get_proximity()
		r_lux = self.ltr559.get_lux()

		self.ltr559_prox.addValue(r_proximity)
		proximity = self.ltr559_prox.getValue()
		self.ltr559_lux.addValue(r_lux)
		lux = self.ltr559_lux.getValue()

		# Write current smoothed data to JSON values
		self.currentValues.proximity, self.currentValues.lux = proximity, lux

		# MICS6814
		gas = MICS6814.read_all()

		self.mics6814_oxidising.addValue(gas.oxidising)
		oxidising = self.mics6814_oxidising.getValue()

		self.mics6814_reducing.addValue(gas.reducing)
		reducing = self.mics6814_reducing.getValue()

		self.mics6814_nh3.addValue(gas.nh3)
		nh3 = self.mics6814_nh3.getValue()

		# Write current smoothed data to JSON values
		self.currentValues.reducing, self.currentValues.oxidising, self.currentValues.nh3 = reducing, oxidising, nh3

		# Send the values to the display
		self.display.updateValues(proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3)

		# update the display - note raw proximity value needed here
		self.display.draw(r_proximity)

	def getJSONValues(self):
		# Return values formatted as JSON
		return self.currentValues.toJSON()