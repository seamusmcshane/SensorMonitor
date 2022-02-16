#  A Wrapper object to handle getting the CPU temperature of the PI but smoothed

from utility.cbuffer import CBuffer
from subprocess import PIPE, Popen

class PICPUTemp:

	def __init__(self, sample_window_len):
		self.sampleBuffer = CBuffer(sample_window_len)

	# Appends a cpu temperature
	def update(self):

		# We read the cpu temp directly from thermal zone0
		process = Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=PIPE)
		(output, process) = process.communicate()

		# Our raw cpu temp as a decimal (30525 / 1000 = 30.525)
		ncpu_temp = float(output) * 0.001

		# Append to the window
		self.sampleBuffer.addValue(ncpu_temp);

	# Gets the temperature
	def getTemperature(self):

		return self.sampleBuffer.getValue()