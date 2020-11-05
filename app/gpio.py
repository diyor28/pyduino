from app.settings import log

try:
	import RPi.GPIO as GPIO
except ImportError:
	class GPIO:
		BOARD = None
		OUT = "OUTPUT"
		LOW = 'ON'
		HIGH = 'OFF'

		@classmethod
		def setmode(cls, mode):
			pass

		@classmethod
		def setup(cls, pin, pin_type):
			log(pin, pin_type)
			pass

		@classmethod
		def output(cls, pin, value):
			log(pin, value)

		@classmethod
		def cleanup(cls):
			log('CLEANING UP GPIO')

GPIO.setmode(GPIO.BOARD)
for pin_setup in [8, 10, 12, 11, 13, 15, 16, 18]:
	GPIO.setup(pin_setup, GPIO.OUT)
	GPIO.output(pin_setup, GPIO.HIGH)


class Relay:
	@classmethod
	def turn_on(cls, pin):
		GPIO.output(pin, GPIO.LOW)

	@classmethod
	def turn_off(cls, pin):
		GPIO.output(pin, GPIO.HIGH)
