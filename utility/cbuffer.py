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

# A Simple Circular Buffer Datastructure
# To avoid having this exact code duplicated everywhere

class CBuffer:

	def __init__(self, buffer_len):

		# We generate a smoothed result using this buffer
		self.buffer_len = buffer_len;
		self.cbuffer = [];

	# Appends a value
	def addValue(self, value):

		# Append to the window
		self.cbuffer.append(value)

		# Remove the oldest sample
		if (len(self.cbuffer) > self.buffer_len):
			del self.cbuffer[0]

	# As an average over the current buffer values
	def getValue(self):

		return sum(self.cbuffer) / float(len(self.cbuffer))