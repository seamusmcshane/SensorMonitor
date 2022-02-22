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

# EnviroPlus Board OLED support
#
# Has two modes, sensors and clock.
# Switches between them on a timer or via proximity sensor trigger.

# LCD Graphics (note ST7735 hardcoded to 160x80)
import ST7735

# Graphics Lib
from PIL import Image, ImageDraw, ImageFont

# Date display
from datetime import datetime, timedelta

# Graphics
FG_TEXT_COLOR = (200, 200, 200)
BG_TEXT_COLOR = (0, 0, 0)

TITLE_FONT_SIZE = 16
TITLE_TEXT_FONT = ImageFont.truetype("NotoMono-Regular.ttf", TITLE_FONT_SIZE)

INFO_FONT_SIZE = 14
INFO_TEXT_FONT = ImageFont.truetype("NotoMono-Regular.ttf", INFO_FONT_SIZE)

CLOCK_TIME_FONT_SIZE = 20
CLOCK_TIME_FONT = ImageFont.truetype("NotoSansMono-Bold.ttf", CLOCK_TIME_FONT_SIZE)

CLOCK_DATE_FONT_SIZE = 16
CLOCK_DATE_FONT = ImageFont.truetype("NotoSansMono-CondensedMedium.ttf", CLOCK_DATE_FONT_SIZE)

# Updating once per second this will cycle modes every this number of seconds
LCD_MODE_CYCLE_FREQUENCY = 120

# An enum to describe better our LCD display modes
from enum import Enum, unique
@unique
class LCD_MODE(Enum):
	SENSORS = 0
	CLOCK = 1

class Display:

	def __init__(self):

		# frame count, we start on 1 as this is the first update
		self.frame=1

		# startup display mode at startup
		self.lcd_mode=LCD_MODE.SENSORS

		# Create an ST7735 LCD instance
		self.lcd = ST7735.ST7735(
		    port=0,
		    cs=1,
		    dc=9,
		    backlight=12,
		    rotation=270,
		    spi_speed_hz=10000000
		)

		# Initialize display
		self.lcd.begin()

		# The backing image / Frame-buffer (for sending)
		self.fb = Image.new('RGB', (self.lcd.width, self.lcd.height), color=(0, 0, 0, 0))

		# Upload a blank image to clear any residual image immediately
		self.lcd.display(self.fb)

		# Raw values
		self.proximity = 0
		self.lux = 0
		self.temperature = 0
		self.humidity = 0
		self.pressure = 0
		self.reducing = 0
		self.oxidising = 0
		self.nh3 = 0

		# Values as formatted/padded strings
		self.s_proximity = 0
		self.s_lux = 0
		self.s_temperature = 0
		self.s_humidity = 0
		self.s_pressure = 0
		self.s_reducing = 0
		self.s_oxidising = 0
		self.s_nh3 = 0

	def updateStringValues(self):
		""" Generates the formatted and padded strings needed for display """

		# our padding value
		val_just = 6

		# Padded Strings
		self.s_proximity = str(round(self.proximity)).ljust(val_just)
		self.s_lux = str(round(self.lux, 2)).ljust(val_just)
		self.s_temperature =  str(round(self.temperature, 2)).ljust(val_just)
		self.s_humidity = str(round(self.humidity, 2)).ljust(val_just)
		self.s_pressure = str(round(self.pressure)).ljust(val_just)
		self.s_reducing = str(round(self.reducing * 0.0001, 2)).ljust(val_just)
		self.s_oxidising = str(round(self.oxidising * 0.0001, 2)).ljust(val_just)
		self.s_nh3 = str(round(self.nh3 * 0.0001)).ljust(val_just)

		debugprint = 0
		if (debugprint == 1):
			lbljust = 12
			print("--------------------")
			print("proximity ".ljust(lbljust), self.proximity)
			print("lux".ljust(lbljust), self.lux)
			print(" ")
			print("temperature".ljust(lbljust), self.temperature)
			print("humidity".ljust(lbljust), self.humidity)
			print("pressure".ljust(lbljust), self.pressure)
			print(" ")
			print("Reducing".ljust(lbljust), self.reducing)
			print("Oxidising".ljust(lbljust), self.oxidising)
			print("NH3".ljust(lbljust), self.nh3)
			print(" ")

	def updateValues(self, proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3):
		""" Provides us with new values. """

		# Raw Values
		self.proximity = proximity
		self.lux = lux
		self.temperature = temperature
		self.humidity = humidity
		self.pressure = pressure
		self.reducing = reducing
		self.oxidising = oxidising
		self.nh3 = nh3

		# Now create the formatted strings we need
		self.updateStringValues()

	def check_proximity(self, raw_proximity):
		""" Checks if the proximity sensor is above the threshold 100. """

		prox_val = float(raw_proximity)
		if(prox_val > 100):
			self.lcd_cycle_mode(True)

	def draw(self, raw_proximity):
		""" Draws the display now, based on the current values and mode """

		# Checks if we need to cycle the LCD Mode
		self.lcd_cycle_mode(False)

		# Check if the proximity sensor is tripped
		self.check_proximity(raw_proximity)

		#print("LCD Mode".ljust(lbljust), self.lcd_mode)

		# Decide which display to write to the frame buffer based on the LCD_MODE
		if (self.lcd_mode == LCD_MODE.SENSORS):
				self.lcd_sensor_mode()
		elif (self.lcd_mode == LCD_MODE.CLOCK):
				self.lcd_clock_mode()

		# debug to test the display is updating (will over write the bottom of display with a black bar and a frame counter.
		debugFrame = 0
		if (debugFrame == 1):
			draw.rectangle((0, 60, self.fb.width, self.fb.height), fill=(0,0,0))
			draw.text((0, 60), str(self.frame), font=TITLE_TEXT_FONT, fill=(255,0,0))

		# Upload the buffer to the display
		self.lcd.display(self.fb)

		# The frame counter
		self.frame = self.frame + 1

	def lcd_cycle_mode(self, override):
		""" When called will cycle to the next LCD mode if the frame count is triggered or right away if override is true """

		if(((self.frame % LCD_MODE_CYCLE_FREQUENCY) == 0) or override):
			if (self.lcd_mode == LCD_MODE.SENSORS):
				self.lcd_mode  = LCD_MODE.CLOCK
			elif (self.lcd_mode == LCD_MODE.CLOCK):
				self.lcd_mode  = LCD_MODE.SENSORS

	def lcd_sensor_mode(self):
		""" Displays the current sensor values on the screen with a small date/clock display at the top."""

		fb = self.fb;

		# Our frame buffer wrapped in the drawing object
		draw = ImageDraw.Draw(fb)

		lx_val = self.lux

		brightnessc = 0

		if(lx_val > 0 and lx_val < 2):
			brightnessc = 0
		elif(lx_val > 2 and lx_val < 4):
			brightnessc = 20
		elif(lx_val > 4 and lx_val < 6):
			brightnessc = 40
		elif(lx_val > 6 and lx_val < 8):
			brightnessc = 60
		elif(lx_val > 8):
			brightnessc = 80
		else:
			brightnessc = 0

		brightness = 0 + brightnessc
		altbrightness = ( brightness + 40 ) % 255

		# Column X coord
		c1x = 2
		c2x = 82

		# Blank the image
		draw.rectangle((0, 0, fb.width, fb.height), fill=(0,0, brightness))

		# Header BK
		draw.rectangle((0, 0, fb.width, TITLE_FONT_SIZE + 2), fill=(brightness,brightness,0))

		# Alt Row bks
		#draw.rectangle((0, 36, fb.width, 36 + INFO_FONT_SIZE + 2 ), fill=(0,0,altbrightness))
		#draw.rectangle((0, 64, fb.width, 64 + INFO_FONT_SIZE + 2 ), fill=(0,0,altbrightness))

		# Date / Time at the top
		today = datetime.now()

		time_stamp = ""

		if((self.frame % 2) == 0):

			time_stamp = today.strftime('%a %d %b %H %M')

		else:

			time_stamp = today.strftime('%a %d %b %H:%M')

		draw.text((0, 2), time_stamp, font=TITLE_TEXT_FONT, fill=FG_TEXT_COLOR)

		# Header Div
		draw.line((8, 20, fb.width - 16, 20), fill=(255,255,255), width=1)

		# Temperature
		tfill = (0,0,0)
		tt = self.temperature
		if (tt < 18):
			tfill = (0,0,64)
		elif (tt < 24):
			tfill = (0,64,0)
		else:
			tfill = (64,0,0)

		draw.rectangle((c1x, 22, 82, 22 + INFO_FONT_SIZE + 2 ), fill=tfill)
		draw.text((c1x, 22), self.s_temperature + "°C", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# humidity
		hfill = (0,0,0)
		ht = self.humidity
		if (ht < 25):
			hfill = (64,0,0)
		elif (ht < 75):
			hfill = (0,64,0)
		else:
			hfill = (64,0,0)

		draw.rectangle((c1x, 36, 82, 36 + INFO_FONT_SIZE + 2 ), fill=hfill)
		draw.text((c1x, 36), self.s_humidity + "%", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# pressure
		pfill = (0,0,0)
		pt = self.pressure
		if (pt < 980):
			pfill = (0,0,64)
		elif (pt < 1020):
			pfill = (0,64,0)
		else:
			pfill = (64,0,0)

		draw.rectangle((c1x, 50, 82, 50 + INFO_FONT_SIZE + 2 ), fill=pfill)
		draw.text((c1x, 50), self.s_pressure + "mb", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# lux (indoor bad lighting)
		lfill = (0,0,0)
		lt = self.lux
		if (lt < 2):
			lfill = (0,0,16)
		elif (lt < 4):
			lfill = (0,0,32)
		elif (lt < 6):
			lfill = (0,0,48)
		elif (lt < 8):
			lfill = (0,48,0)
		else:
			lfill = (0,64,0)

		draw.rectangle((c1x, 64, 82, 64 + INFO_FONT_SIZE + 2 ), fill=lfill)
		draw.text((c1x, 64), self.s_lux + "Lux", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		draw.text((c2x, 22), self.s_reducing + "CO", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# oxidising ( nitrogen dioxide)
		draw.text((c2x, 36), self.s_oxidising + "NO", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# nh3 ( ammonia, hydrogen, ethanol, propane etc)
		draw.text((c2x, 50), self.s_nh3 + "NH3", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# prox
		draw.text((c2x, 64), self.s_proximity + "px", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)


	def lcd_clock_mode(self):
		"""  A large centred date/clock display with old school blinking : """

		fb = self.fb;

		# Our frame buffer wrapped in the drawing object
		draw = ImageDraw.Draw(self.fb)

		# Blank the image
		draw.rectangle((0, 0, fb.width, fb.height), fill=(0,0,0))

		# Date / Time at the top
		today = datetime.now()

		year_stamp = today.strftime('%Y')
		date_stamp = today.strftime('%A %d %B')
		time_stamp = ""

		# Binking : as on lcd clocks / watches
		if((self.frame % 2) == 0):
			time_stamp = today.strftime('%H %M')
		else:
			time_stamp = today.strftime('%H:%M')

		# Center the text (y was manually guesstimated based on font size)
		xs,ys = draw.textsize(time_stamp,font=CLOCK_TIME_FONT)
		draw.text((80-(xs*0.5), 5), time_stamp, font=CLOCK_TIME_FONT, fill=FG_TEXT_COLOR)

		xs,ys = draw.textsize(date_stamp,font=CLOCK_DATE_FONT)
		draw.text((80-(xs*0.5), 30), date_stamp, font=CLOCK_DATE_FONT, fill=FG_TEXT_COLOR)

		xs,ys = draw.textsize(year_stamp,font=CLOCK_DATE_FONT)
		draw.text((80-(xs*0.5), 50), year_stamp, font=CLOCK_DATE_FONT, fill=FG_TEXT_COLOR)
