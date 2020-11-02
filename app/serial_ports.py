import time
import time
import re
import asyncio
import json
from typing import List, Tuple

import aioserial
import serial
from aioserial import AioSerial
from serial.tools import list_ports

from app.settings import RETRY_IN, BAUD_RATE, MAX_FAILED_ATTEMPTS, log


def time_it(func):
	async def wrapper(*args, **kwargs):
		start = time.time()
		result = await func(*args, **kwargs)
		end = time.time() - start
		print(f"{func.__name__} {int(end * 1000)} ms")
		return result

	return wrapper


class SerialPortWrapper:
	serial_port: AioSerial
	failed_reads: int = 0
	connected: bool = False

	async def connect_to_serial(self):
		ports = list_ports.comports()
		port = next((item.device for item in ports if re.match(r'COM\d+', item.device) or re.match(r'/dev/ttyACM\d+', item.device)), None)
		if port is None:
			print(f"Could not find any serial device. Retrying in {RETRY_IN} seconds...")
			self.connected = False
			await asyncio.sleep(RETRY_IN)
			asyncio.create_task(self.connect_to_serial())
			return
		log(port)

		try:
			self.serial_port: AioSerial = AioSerial(port=port, baudrate=BAUD_RATE, bytesize=8, timeout=2, stopbits=aioserial.STOPBITS_ONE)
			log('SERIAL_PORT STATE::', self.serial_port.isOpen())
			self.connected = True
		except serial.SerialException as e:
			self.connected = False
			print(e, f"Retrying in {RETRY_IN} seconds...")
			await asyncio.sleep(RETRY_IN)
			asyncio.create_task(self.connect_to_serial())
			return

	async def read(self) -> Tuple[List[dict], str]:
		try:
			log('SERIAL PORT STATE::', self.serial_port.isOpen())
			message: str = (await self.serial_port.readline_async()).decode('Ascii')
		except (serial.SerialException, UnicodeDecodeError) as e:
			print(e, f"Failed to read of port {self.serial_port.port}. Failed reads {self.failed_reads}. Retrying in {RETRY_IN} seconds...")
			self.failed_reads += 1
			await asyncio.sleep(RETRY_IN)
			if self.failed_reads > MAX_FAILED_ATTEMPTS:
				print(f'Reached maximum number({MAX_FAILED_ATTEMPTS}) of failed attempts. Retrying to connect.')
				# self.serial_port.close()
				asyncio.create_task(self.connect_to_serial())
				self.failed_reads = 0
				return [], 'Попытка переподключиться к датчикам'
			return [], 'Не удалось считать данные с сенсора'
		try:
			log('message', message, verbose=2)
			result = json.loads(message)
			if type(result) is not list:
				return [], 'Датчик отправляет искаженные данные'
		except json.decoder.JSONDecodeError:
			return [], 'Датчик отправляет искаженные данные'
		self.failed_reads = 0
		return result, ''
