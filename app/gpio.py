import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)


class Relay:
	def __init__(self, pin):
		GPIO.setup(pin, GPIO.OUT)
		self.pin = pin

	def fire(self):
		GPIO.output(self.pin, GPIO.LOW)

	def turn_off(self):
		GPIO.output(self.pin, GPIO.HIGH)
