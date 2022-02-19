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
# Devices supported -
# BME280 (Temperature, Humidity and Pressure),
# TSL2591 (light, infrared,+lux via calculation)
# LTR390 (als, +lux via calculation, uvs, +uvi via calculation)
# SGP40 (voc index)

# PI I2C
from smbus import SMBus
I2C_DEV=SMBus(1)

# Temperature, Humidity and Pressure
from sensors.BME280 import BME280

# Light, IR, Lux
from python_tsl2591 import tsl2591

# ALS, LUX, UV, UVI
from sensors.LTR390 import LTR390

# VOC Index
from sensors.SGP40 import SGP40

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

		self.fullspectrum= 0.0
		self.infrared = 0.0
		self.lux1 = 0.0

		self.als = 0.0
		self.lux2 = 0.0
		self.uvs = 0.0
		self.uvi = 0.0

		self.voci = 0.0

	def toJSON(self):
		return "{ \"values\" :" + json.dumps(self, default=lambda o: o.__dict__, sort_keys=False) + "}"

class WaveshareESH:

	def initSGP40(self):

		# Buffer for the SGP40 Stats
		self.sgp40_voci = CBuffer(SAMPLE_WINDOW_LEN)

		# Values are just for initialization
		self.sgp40 = SGP40(i2c_dev=I2C_DEV, relative_humidity = 50, temperature_c = 25)

		print("SGP40 requires warmup, waiting 10 seconds...")
		self.sgp40.begin(10)

		print("SGP40 Ready")

	def initLTR390(self):

		# Buffers for the LTR390 Stats
		self.ltr390_als = CBuffer(SAMPLE_WINDOW_LEN)
		self.ltr390_lux = CBuffer(SAMPLE_WINDOW_LEN)
		self.ltr390_uvs = CBuffer(SAMPLE_WINDOW_LEN)
		self.ltr390_uvi = CBuffer(SAMPLE_WINDOW_LEN)

		# Create an LTR390 instance
		self.ltr390 = LTR390(i2c_dev=I2C_DEV)

		print("LTR390 Ready")

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

	# Setup the TSL2591 Light, IR and Lux Sensor
	def initTSL2591(self):

		self.tsl2591 = tsl2591()

		# Buffers for TSL2591 stats
		self.tsl2591_full = CBuffer(SAMPLE_WINDOW_LEN)
		self.tsl2591_ir = CBuffer(SAMPLE_WINDOW_LEN)
		self.tsl2591_lux = CBuffer(SAMPLE_WINDOW_LEN)

		print("TSL2591 Ready")

	def __init__(self, smooth_factor = 0.9):

		# You will need to calibrate this.
		# Best done with a physical thermometer or a calibrated reference sensor.
		# Value depends on how close the sensor is to the PI, and the Pi's thermals.
		# 0.9 was used with a tall header outside a case with - 1cm distance to the PI.
		# PI is inside a aluminum case, with very low load.
		self.smooth_factor = smooth_factor

		self.initBME280()
		self.initTSL2591()
		self.initLTR390()
		self.initSGP40()

		# Sensor values for formating into json
		self.currentValues = Values()

		print("Waveshare Environment Sensor HAT Ready");

	def smooth_temp_value(self, raw_value, smooth_factor):
		""" Adjusts the BME280 temperature reading to account for distance
		to the PI CPU which genrates enough heat to affect the reading.
		Smoothing assumes you are sampling the sensor more than you are
		storing the data.
		"""

		self.bme280_temps.addValue(raw_value)

		cpu_avg_temp = self.cpu_temp.getTemperature()

		avg_temp = self.bme280_temps.getValue()

		# Dampens the average temp by the cpu average temp.
		# Dampening is scaled using a smooth factor for fine tuning.
		# Adjust smooth_factor based on how close the sensor is to the cpu/case and how hot they get.
		return (avg_temp - ((cpu_avg_temp - avg_temp) / smooth_factor))

	def updateValues(self):
		""" Performs a collection of values from supported devices """

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
		self.currentValues.fullspectrum, self.currentValues.infrared, self.currentValues.lux1 = fullspectrum, infrared, lux

		# LTS390
		aluu = self.ltr390.getAllValues()

		# Add to our buffers
		self.ltr390_als.addValue(aluu[0])
		self.ltr390_lux.addValue(aluu[1])
		self.ltr390_uvs.addValue(aluu[2])
		self.ltr390_uvi.addValue(aluu[3])

		# get our smoothed values
		als = self.ltr390_als.getValue();
		lux = self.ltr390_lux.getValue();
		uvs = self.ltr390_uvs.getValue();
		uvi = self.ltr390_uvi.getValue();

		self.currentValues.als, self.currentValues.lux2 = als, lux
		self.currentValues.uvs, self.currentValues.uvi = uvs, uvi

		# SGP40

		# Note! - Here we set the current values for the SGP40
		# Enables temperature and humidity compensation
		self.sgp40.set_envparams(humidity,temperature)
		tvoci = self.sgp40.get_voc_index()

		# Add to our buffer
		self.sgp40_voci.addValue(tvoci)

		# get our smoothed value
		voci = self.sgp40_voci.getValue();

		self.currentValues.voci = voci

	def getJSONValues(self):
		""" Return values formated as json """

		return self.currentValues.toJSON()
