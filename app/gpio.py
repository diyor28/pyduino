try:
	import RPi.GPIO as GPIO
except ImportError:
	class GPIO:
		BOARD = None
		OUT = "OUTPUT"
		LOW = 'OFF'
		HIGH = 'ON'

		@classmethod
		def setmode(cls, mode):
			pass

		@classmethod
		def setup(cls, pin, pin_type):
			print(pin, pin_type)
			pass

		@classmethod
		def output(cls, pin, value):
			print(pin, value)

GPIO.setmode(GPIO.BOARD)


class Relay:
	def __init__(self, pin):
		GPIO.setup(pin, GPIO.OUT)
		self.pin = pin

	def turn_on(self):
		GPIO.output(self.pin, GPIO.LOW)

	def turn_off(self):
		GPIO.output(self.pin, GPIO.HIGH)
