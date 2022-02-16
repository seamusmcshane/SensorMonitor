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