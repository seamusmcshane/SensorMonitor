# Enviroplus Board support
# Devices supported		-	Temperature, Humidity and Pressure, Lux, Proximity, Gas and LCD.
# Devices not supported	-	Noise and Particulate matter addon.

# Temperature, Humidity and Pressure
from smbus import SMBus
from sensors.BME280 import BME280
from subprocess import PIPE, Popen

# The Lux/Proximity sensors
from ltr559 import LTR559

# LCD Graphics (note ST7735 hardcoded to 160x80)
import ST7735

# Graphics Lib
from PIL import Image, ImageDraw, ImageFont

# Date display
from datetime import datetime, timedelta

# Gas sensor
from sensors import MICS6814

# math
import math

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

# Assuming updating at 1 sample per second this is ten seconds of samples
SAMPLE_WINDOW_LEN = 10;

# Updating once per second this will cycle every this number of seconds
LCD_MODE_CYCLE_FREQUENCY = 120;

# An enum to describe better our LCD display modes
from enum import Enum, unique
@unique
class LCD_MODE(Enum):
	SENSORS = 0
	CLOCK = 1;

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

	# Setup the LCD controller and backing framebuffer
	def initDisplay(self):

		# Create an LCD instance
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

		# The backing image / Framebuffer
		self.fb = Image.new('RGB', (self.lcd.width, self.lcd.height), color=(0, 0, 0, 0))

		print("ST7735 Ready")

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

	# Displays the current sensor values on the screen with a small date/clock display at the top.
	def lcd_sensor_mode(self, fb, draw , proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3):

		lx_val = float(lux)

		brightnessc = 0;

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
		tt = float(temperature)
		if (tt < 18):
			tfill = (0,0,64)
		elif (tt < 24):
			tfill = (0,64,0)
		else:
			tfill = (64,0,0)

		draw.rectangle((c1x, 22, 82, 22 + INFO_FONT_SIZE + 2 ), fill=tfill)
		draw.text((c1x, 22), temperature + "c", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# humidity
		hfill = (0,0,0)
		ht = float(humidity)
		if (ht < 25):
			hfill = (64,0,0)
		elif (ht < 75):
			hfill = (0,64,0)
		else:
			hfill = (64,0,0)

		draw.rectangle((c1x, 36, 82, 36 + INFO_FONT_SIZE + 2 ), fill=hfill)
		draw.text((c1x, 36), humidity + "%", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# pressure
		pfill = (0,0,0)
		pt = float(pressure)
		if (pt < 980):
			pfill = (0,0,64)
		elif (pt < 1020):
			pfill = (0,64,0)
		else:
			pfill = (64,0,0)

		draw.rectangle((c1x, 50, 82, 50 + INFO_FONT_SIZE + 2 ), fill=pfill)
		draw.text((c1x, 50), pressure + "mb", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# lux (indoor bad ligting)
		lfill = (0,0,0)
		lt = float(lux)
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
		draw.text((c1x, 64), lux + "lx", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# Reducing ( carbon monoxide~)
		pfill = (0,0,0)
		pt = float(pressure)
		if (pt < 980):
			pfill = (0,0,64)
		elif (pt < 1020):
			pfill = (0,64,0)
		else:
			pfill = (64,0,0)

		draw.text((c2x, 22), reducing + "CO", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# oxidising ( nitrogen dioxide)
		draw.text((c2x, 36), oxidising + "NO", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# nh3 ( ammonia, hydrogen, ethanol, propane etc)
		draw.text((c2x, 50), nh3 + "NH3", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

		# prox
		draw.text((c2x, 64), proximity + "px", font=INFO_TEXT_FONT, fill=FG_TEXT_COLOR)

	# A large centered date/clock display with old school blinking :
	def lcd_clock_mode(self, fb, draw):

		# Blank the image
		draw.rectangle((0, 0, fb.width, fb.height), fill=(0,0,0))

		# Date / Time at the top
		today = datetime.now()

		year_stamp = today.strftime('%Y')
		date_stamp = today.strftime('%A %d %B')
		time_stamp = ""

		if((self.frame % 2) == 0):

			time_stamp = today.strftime('%H %M')

		else:

			time_stamp = today.strftime('%H:%M')

		# Center the text (y is a manual guesstimated based on font size)
		xs,ys = draw.textsize(time_stamp,font=CLOCK_TIME_FONT)
		draw.text((80-(xs*0.5), 5), time_stamp, font=CLOCK_TIME_FONT, fill=FG_TEXT_COLOR)

		xs,ys = draw.textsize(date_stamp,font=CLOCK_DATE_FONT)
		draw.text((80-(xs*0.5), 30), date_stamp, font=CLOCK_DATE_FONT, fill=FG_TEXT_COLOR)

		xs,ys = draw.textsize(year_stamp,font=CLOCK_DATE_FONT)
		draw.text((80-(xs*0.5), 50), year_stamp, font=CLOCK_DATE_FONT, fill=FG_TEXT_COLOR)

	# When called will cycle to the next LCD mode if the frame count is triggered or right away if override is true
	def lcd_cycle_mode(self, override):

		if(((self.frame % LCD_MODE_CYCLE_FREQUENCY) == 0) or override):
			if (self.lcd_mode == LCD_MODE.SENSORS):
				self.lcd_mode  = LCD_MODE.CLOCK
			elif (self.lcd_mode == LCD_MODE.CLOCK):
				self.lcd_mode  = LCD_MODE.SENSORS

	# Threshold 100 is used to account for some (large) noise on the sensor
	def check_proximity(self, proximity):

		prox_val = float(proximity)
		if(prox_val > 100):
			self.lcd_cycle_mode(True)

	def update_lcd_display(self, proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3):

		# Our frame buffer wrapped in the drawing object
		draw = ImageDraw.Draw(self.fb)

		# Checks if we need to cycle the LCD Mode
		self.lcd_cycle_mode(False);

		# Check if the proximity sensor is tripped
		self.check_proximity(proximity);

		#print("LCD Mode".ljust(lbljust), self.lcd_mode);

		# Decide which display to write to the frame buffer based on the LCD_MODE
		if (self.lcd_mode == LCD_MODE.SENSORS):
				self.lcd_sensor_mode(self.fb, draw, proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3)
		elif (self.lcd_mode == LCD_MODE.CLOCK):
				self.lcd_clock_mode(self.fb, draw)

		# debug to test the display is updating (will over write the bottom of display with a black bar and a frame counter.
		debugFrame = 0
		if (debugFrame == 1):
			draw.rectangle((0, 60, self.fb.width, self.fb.height), fill=(0,0,0))
			draw.text((0, 60), str(self.frame), font=TITLE_TEXT_FONT, fill=(255,0,0))

		# Upload the buffer to the display
		self.lcd.display(self.fb)

		# The frame counter
		self.frame = self.frame + 1

	def updateValues(self):

		val_just = 6

		# ltr559
		proximity = self.ltr559.get_proximity()
		s_proximity = str(round(proximity)).ljust(val_just)

		lux = self.ltr559.get_lux();
		lux = self.smooth_value_generic(self.ltr559_raw_lux_window, SAMPLE_WINDOW_LEN, lux)
		s_lux = str(round(lux, 2)).ljust(val_just)

		# BME280 lib is modified to coalesc the three calls
		thp = self.bme280.get_thp()
		temperature =  self.smooth_temp_value(SAMPLE_WINDOW_LEN, thp[0])	# calls temperature specifc smooth
		s_temperature =  str(round(temperature, 2)).ljust(val_just)

		humidity = self.smooth_value_generic(self.bme280_raw_humidity_window, SAMPLE_WINDOW_LEN, thp[1])
		s_humidity = str(round(humidity, 2)).ljust(val_just)

		pressure = self.smooth_value_generic(self.bme280_raw_pressure_window, SAMPLE_WINDOW_LEN, thp[2])
		s_pressure = str(round(pressure)).ljust(val_just)

		# MICS6814
		gas_data = MICS6814.read_all()

		reducing = self.smooth_value_generic(self.mics6814_raw_reducing_window, SAMPLE_WINDOW_LEN, gas_data.reducing)
		s_reducing = str(round(reducing * 0.0001, 2)).ljust(val_just)

		oxidising = self.smooth_value_generic(self.mics6814_raw_oxidising_window, SAMPLE_WINDOW_LEN, gas_data.oxidising)
		s_oxidising = str(round(oxidising * 0.0001, 2)).ljust(val_just)

		nh3 = self.smooth_value_generic(self.mics6814_raw_nh3_window, SAMPLE_WINDOW_LEN, gas_data.nh3)
		s_nh3 = str(round(nh3 * 0.0001)).ljust(val_just)

		debugprint = 0
		if (debugprint == 1):
			lbljust = 12
			print("--------------------")
			print("proximity ".ljust(lbljust), proximity)
			print("lux".ljust(lbljust), lux)
			print(" ");
			print("temperature".ljust(lbljust), temperature)
			print("humidity".ljust(lbljust), humidity)
			print("pressure".ljust(lbljust), pressure)
			print(" ");
			print("Reducing".ljust(lbljust), reducing)
			print("Oxidising".ljust(lbljust), oxidising)
			print("NH3".ljust(lbljust), nh3)
			print(" ");

		# update the lcd with the new values converted to strings
		self.update_lcd_display(s_proximity, s_lux, s_temperature, s_humidity, s_pressure, s_reducing, s_oxidising, s_nh3)

		# Store our values (to turn into json later)
		self.currentValues.proximity, self.currentValues.lux, self.currentValues.temperature, self.currentValues.humidity, self.currentValues.pressure, self.currentValues.reducing, self.currentValues.oxidising, self.currentValues.nh3 = proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3

		# return the sensor values when called (for debugging)
		return proximity, lux, temperature, humidity, pressure, reducing, oxidising, nh3

	def getJSONValues(self):
		# Return values formated as json
		return self.currentValues.toJSON()