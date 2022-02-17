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

# Waveshare Environment Sensor HAT Board Support
# Devices supported - BM280 (Temperature, Humidity and Pressure), TSL2591 (light, infrared,+lux via calculation)

# Temperature, Humidity and Pressure
from smbus import SMBus
from sensors.BME280 import BME280

# Light, IR, Lux
from python_tsl2591 import tsl2591

from utility.cbuffer import CBuffer
from utility.picputemperature import PICPUTemp

# Assuming updating at 1 sample per second this is ten seconds of samples
SAMPLE_WINDOW_LEN = 10;

# A class to describe what our json returned values will look like
import json
class Values:

	def __init__(self):

		self.temperature = 0.0
		self.humidity = 0.0
		self.pressure = 0.0

		self.fullspectrum = 0.0
		self.infrared = 0.0
		self.lux = 0.0

	def toJSON(self):
		return "{ \"values\" :" + json.dumps(self, default=lambda o: o.__dict__, sort_keys=False) + "}"

class WaveshareESH:

	# This you will need to calibrate this as they depend on the PI.
	# Best done with a physical thermometer or a calibrated reference sensor.
	# Value depends on how close the sensor is to the PI, and the Pi's thermals. Here there is a tall header so 1cm distance and pi is inside a aluminum case, with very low load.
	smooth_factor = 0.9;

	# Setup the BME Temperature, Humidity and Pressure sensor
	def initBME280(self):

		# CPU Temp
		self.cpu_temp = PICPUTemp(SAMPLE_WINDOW_LEN)

		# Buffers for BME280 stats
		self.bme280_temps = CBuffer(SAMPLE_WINDOW_LEN)
		self.bme280_humidity = CBuffer(SAMPLE_WINDOW_LEN)
		self.bme280_pressure = CBuffer(SAMPLE_WINDOW_LEN)

		# Create a BME280 instance (SMBus 1)
		self.bme280 = BME280(i2c_dev=SMBus(1))
		self.bme280.setup(mode="forced", temperature_oversampling=16, pressure_oversampling=16)

		print("BME280 Ready")

	# Setup the TSL2591 Light, IR and Lux Sensor
	def initTSL2591(self):

		self.tsl2591 = tsl2591()

		# Buffers for TSL2591 stats
		self.tsl2591_full = CBuffer(SAMPLE_WINDOW_LEN)
		self.tsl2591_ir = CBuffer(SAMPLE_WINDOW_LEN)
		self.tsl2591_lux = CBuffer(SAMPLE_WINDOW_LEN)

		print("TSL2591 Ready")

	def __init__(self):

		self.initBME280()
		self.initTSL2591()

		# Sensor values for formating into json
		self.currentValues = Values()

		print("Waveshare Environment Sensor HAT Ready");

	# Assumes you are sampling the sensor more than you are storing the data
	def smooth_temp_value(self, raw_value, smooth_factor):

		self.bme280_temps.addValue(raw_value)

		cpu_avg_temp = self.cpu_temp.getTemperature()

		avg_temp = self.bme280_temps.getValue()

		# Dampens the average temp by the cpu average temp.
		# Dampening is scaled using a smooth factor for fine tuning.
		# Adjust smooth_factor based on how close the sensor is to the cpu/case and how hot they get.
		# see smooth_factor at the top of this class.
		return (avg_temp - ((cpu_avg_temp - avg_temp) / smooth_factor))

	def updateValues(self):

		# Update the cpu temp which is used to smooth/adjust the bme280 temp
		self.cpu_temp.update()

		# BME280 lib is modified to coalesc the three calls
		thp = self.bme280.get_thp()
		temperature =  self.smooth_temp_value(thp[0], self.smooth_factor)	# calls temperature specifc smooth
		self.bme280_humidity.addValue(thp[1])
		humidity = self.bme280_humidity.getValue()
		self.bme280_pressure.addValue(thp[2])
		pressure = self.bme280_pressure.getValue()
		# Write current smoothed data to json values
		self.currentValues.temperature, self.currentValues.humidity, self.currentValues.pressure = temperature, humidity, pressure

		# TSL2591
		fullspectrum, infrared = self.tsl2591.get_full_luminosity()
		lux = self.tsl2591.calculate_lux(fullspectrum, infrared)
		self.tsl2591_full.addValue(fullspectrum);
		self.tsl2591_ir.addValue(infrared);
		self.tsl2591_lux.addValue(lux);
		# Write current smoothed data to json values
		self.currentValues.fullspectrum, self.currentValues.infrared, self.currentValues.lux = fullspectrum, infrared, lux

	def getJSONValues(self):
		# Return values formated as json
		return self.currentValues.toJSON()
