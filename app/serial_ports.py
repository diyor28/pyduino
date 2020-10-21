import time
import re
import asyncio
import json
from typing import Union, List

import aioserial
import serial
from aioserial import AioSerial
from serial.tools import list_ports

from app.settings import RETRY_IN, BAUD_RATE, MAX_FAILED_ATTEMPTS, DEBUG


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

	async def connect_to_serial(self):
		ports = list_ports.comports()
		port = next((item.device for item in ports if re.match(r'COM\d+', item.device) or re.match(r'/dev/ttyACM\d+', item.device)), None)
		if port is None:
			print(f"Could not find any serial device. Retrying in {RETRY_IN} seconds...")
			await asyncio.sleep(RETRY_IN)
			return await self.connect_to_serial()
		print(port)
		try:
			self.serial_port: AioSerial = AioSerial(port=port, baudrate=BAUD_RATE, bytesize=8, timeout=2, stopbits=aioserial.STOPBITS_ONE)
		except serial.SerialException as e:
			print(e)
			print(f"Retrying in {RETRY_IN} seconds...")
			await asyncio.sleep(RETRY_IN)
			await self.connect_to_serial()
		return True

	async def read(self) -> Union[List[dict], str]:
		try:
			message: str = (await self.serial_port.readline_async()).decode('Ascii')
		except (serial.SerialException, UnicodeDecodeError) as e:
			print(e, self.serial_port.port, self.failed_reads)
			print(f"Retrying in {RETRY_IN} seconds...")
			self.failed_reads += 1
			await asyncio.sleep(RETRY_IN)
			if self.failed_reads > MAX_FAILED_ATTEMPTS:
				print(f'Reached maximum number({MAX_FAILED_ATTEMPTS}) of failed attempts. Retrying to connect.')
				self.serial_port.close()
				await self.connect_to_serial()
			return await self.read()
		try:
			if DEBUG:
				print('message', message)
			result = json.loads(message)
			if type(result) is not list:
				return message
		except json.decoder.JSONDecodeError:
			return message
		self.failed_reads = 0
		return result
