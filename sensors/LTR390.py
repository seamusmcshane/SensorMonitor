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

import time
import smbus

# I2C Address
LTR390_ADDR = 0X53
LTR390_PART_ID = 0xB2

# Register Set
LTR390_REG_MAIN_CTRL			= 0x00 # ALS/UVS operation mode control, SW reset
LTR390_REG_ALS_UVS_MEAS_RATE	= 0x01 # ALS/UVS measurement rate and resolution in Active Mode (default 0x22)
LTR390_REG_ALS_UVS_GAIN			= 0x05 # ALS/UVS analog Gain range (default 0x01)
LTR390_REG_PART_ID				= 0x06 # Part number ID and revision ID
LTR390_REG_MAIN_STATUS			= 0x07 # Power-On status, Interrupt status, Data status
LTR390_REG_ALS_DATA_0			= 0x0D # ALS ADC measurement data, LSB
LTR390_REG_ALS_DATA_1			= 0x0E # ALS ADC measurement data
LTR390_REG_ALS_DATA_2			= 0x0F # ALS ADC measurement data, MSB
LTR390_REG_UVS_DATA_0			= 0x10 # UVS ADC measurement data, LSB
LTR390_REG_UVS_DATA_1			= 0x11 # UVS ADC measurement data
LTR390_REG_UVS_DATA_2			= 0x12 # UVS ADC measurement data, MSB
# 0x13 – 0x18 Reserved				   # Reserved
LTR390_INT_CFG				= 0x10 # Interrupt configuration
LTR390_INT_PST				= 0x00 # Interrupt persist setting
LTR390_ALS_UVS_THRES_UP_0	= 0xFF # ALS/UVS interrupt upper threshold, LSB
LTR390_ALS_UVS_THRES_UP_1	= 0xFF # ALS/UVS interrupt upper threshold, intervening bits
LTR390_ALS_UVS_THRES_UP_2	= 0x0F # ALS/UVS interrupt upper threshold, MSB
LTR390_ALS_UVS_THRES_LOW_0	= 0x00 # ALS/UVS interrupt lower threshold, LSB
LTR390_ALS_UVS_THRES_LOW_1	= 0x00 # ALS/UVS interrupt lower threshold, intervening bits
LTR390_ALS_UVS_THRES_LOW_2	= 0x00 # ALS/UVS interrupt lower threshold, MSB

# Control Modes
LTR390_ALS_ACTIVE = 0x2
LTR390_UVS_ACTIVE = 0xA

# From datasheet
LTS390_UVSensitivity = 2300.0

from enum import IntEnum
class MEAS_RATE(IntEnum):
	# ALS/UVS Resolution (bits 6-4) | ALS/UVS Measurement Rate (bits 2-0)
	# We do not support setting these independantly to avoid a
	# misconfiguration issue where the programmed measurement rate is
	# set lower than the needed rate for the bit resolution.
	# The values choosen are based on the conversion time in the datasheet
	# for each resolution, paired with the nearest valid measurement rate.
	RES_20BIT_500ms = 0x00 | 0x04
	RES_19BIT_200ms = 0x10 | 0x03
	RES_18BIT_100ms = 0x20 | 0x02
	RES_17BIT_50ms  = 0x30 | 0x01
	RES_16BIT_25ms  = 0x40 | 0x00
	RES_13BIT_12_5ms  = 0x50 | 0x00

	@classmethod
	def getIntFactor(self, sampleRes):
		# ALS/UVI Formula
		if sampleRes == MEAS_RATE.RES_20BIT_500ms:
			return 4.0
		elif sampleRes == MEAS_RATE.RES_19BIT_200ms:
			return 2.0
		elif sampleRes == MEAS_RATE.RES_18BIT_100ms:
			return 1.0
		elif sampleRes == MEAS_RATE.RES_17BIT_50ms:
			return 0.5
		elif sampleRes == MEAS_RATE.RES_16BIT_25ms:
			return 0.25
		else:
			# LTR390SampleRes.RES_13BIT_12_5ms
			return 0.03125

from enum import IntEnum
class GAIN(IntEnum):
	# ALS_UVS_GAIN - Gain Range
	RANGE_1  = 0x0
	RANGE_3  = 0x1
	RANGE_6  = 0x2
	RANGE_9  = 0x3
	RANGE_18 = 0x4

	@classmethod
	def getGainFactor(self, gainrange):
	# ALS/UVI Formula
		if gainrange == GAIN.RANGE_1:
			return 1.0
		elif gainrange == GAIN.RANGE_3:
			return 3.0
		elif gainrange == GAIN.RANGE_6:
			return 6.0
		elif gainrange == GAIN.RANGE_9:
			return 9.0
		else:
			# LTR390GAIN.RANGE_19:
			return 18.0

class LTR390:
	""" Enables support for the Liteon LTR-390UV Sensor.
	See Datasheet "LTR-390UV_Final_ DS_V1 1.pdf" for hardware details.

	We default to 18bit to enable some time for other sensors
	to be called after us within a 1 second sampling window.
	When switching between ALS and UVS, 18bit has a 100ms
	collection time for a valid reading - 200ms overall for both reads.
	"""

	def __init__(self, address=LTR390_ADDR, i2c_dev=None, res=MEAS_RATE.RES_18BIT_100ms, gainrange=GAIN.RANGE_18, wfact=1):

		self.address = address
		self.i2c = i2c_dev

		# We do not reconfigure the library on the fly, recreate a new object for that
		# These are reused is all future calls.
		self.res = res;
		self.gainrange = gainrange;
		self.wfact = wfact;

		# Check Part ID
		self.ID = self.i2c.read_byte_data(self.address, LTR390_REG_PART_ID)

		# Check the Part ID is what we expected and warn if not
		if(LTR390_PART_ID == self.ID):
			print("LTR390 - Part ID = %#x OK!" %self.ID)
		else:
			# Assuming some device is not using the LTR390 address then
			# this is most likely a new revision of the LTS390.
			# Either way log this event!
			print("Warning device with unexpected LTR390 PartID replied = %#x" %self.ID)

		print("LTR390 - Rate %#x, Gain %#x" %(res, gainrange))


	def modeALS(self):
		""" Switch to ALS Mode, you need to wait until a sample is collected
		by the sensor before calling readALS
		"""

		self.i2c.write_byte_data(self.address , LTR390_REG_MAIN_CTRL, LTR390_ALS_ACTIVE)

	def modeUVS(self):
		""" Switch to UVS Mode, you need to wait until a sample is collected
		by the sensor before calling readUVS
		"""

		self.i2c.write_byte_data(self.address , LTR390_REG_MAIN_CTRL, LTR390_UVS_ACTIVE)

	def readALS(self):
		""" Please ensure the mode is ALS before calling
		We do not check if the data is new.
		"""

		self.i2c.write_byte_data(self.address , LTR390_REG_ALS_UVS_MEAS_RATE, self.res)
		self.i2c.write_byte_data(self.address , LTR390_REG_ALS_UVS_GAIN, self.gainrange)

		alsd0 = self.i2c.read_byte_data(self.address, LTR390_REG_ALS_DATA_0)
		alsd1 = self.i2c.read_byte_data(self.address, LTR390_REG_ALS_DATA_1)
		alsd2 = self.i2c.read_byte_data(self.address, LTR390_REG_ALS_DATA_2)

		return (alsd2 << 16)|(alsd1 << 8)|alsd0

	def readUVS(self):
		""" Please ensure the mode is UVS before calling
		We do not check if the data is new.
		"""

		self.i2c.write_byte_data(self.address , LTR390_REG_ALS_UVS_MEAS_RATE, self.res)
		self.i2c.write_byte_data(self.address , LTR390_REG_ALS_UVS_GAIN, self.gainrange)

		uvsd0 = self.i2c.read_byte_data(self.address, LTR390_REG_UVS_DATA_0)
		uvsd1 = self.i2c.read_byte_data(self.address, LTR390_REG_UVS_DATA_1)
		uvsd2 = self.i2c.read_byte_data(self.address, LTR390_REG_UVS_DATA_2)

		return (uvsd2 << 16)|(uvsd1 << 8)|uvsd0

	def calcLUX(self, als):
		""" See LTR-390UV-01 ALS Formula """

		gainFact = GAIN.getGainFactor(self.gainrange)

		intFact = MEAS_RATE.getIntFactor(self.res)

		p1 = 0.6 * als
		p2 = gainFact * intFact

		return (p1/p2) * self.wfact

	def calcUVI(self, uv):
		""" LTR-390UV-01 UVI Formula """

		return (uv/LTS390_UVSensitivity) * self.wfact

	def getAllValues(self):
		""" Returns all values from an ALS read and UVS read.
		Internallly waits after each mode switch to give time to collect
		a valid sample reading.
		"""

		# tSleep is adjusted "based" on the collection time in the data sheet
		tSleep = 0.125 * MEAS_RATE.getIntFactor(self.res)

		# A min sleep as sensor will always need a delay to collect
		if tSleep <0.1:
			tSleep = 0.1;

		# Analogue Light
		self.modeALS()
		time.sleep(tSleep)
		als = self.readALS()
		lux = self.calcLUX(als)

		# Ultra-violet
		self.modeUVS()
		time.sleep(tSleep)
		uvs = self.readUVS()
		uvi = self.calcUVI(uvs)

		return als, lux, uvs, uvi
