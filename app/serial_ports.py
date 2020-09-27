import json
import asyncio
import time
import math
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Union
import aioserial
import serial
from aioserial import AioSerial
from serial.tools import list_ports
from sqlalchemy import event
from app.database import get_db
from app.models import Sensor, Temperature, Relays
from app.gpio import Relay

DEBUG = os.environ.get('DEBUG', False)
RTD_A = 3.9083e-3
RTD_B = - 5.775e-7
BAUD_RATE = 250_000
MAX_FAILED_ATTEMPTS = 4
RETRY_IN = 2


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
			await asyncio.sleep(2)
			await self.connect_to_serial()
		return True

	async def read(self) -> Union[List[dict], str]:
		try:
			message: str = (await self.serial_port.readline_async()).decode('Ascii')
		except serial.SerialException as e:
			print(e, self.serial_port.port)
			print(f"Retrying in {RETRY_IN} seconds...")
			self.failed_reads += 1
			await asyncio.sleep(RETRY_IN)
			return await self.read()
		except UnicodeDecodeError as e:
			print(e, self.serial_port.port)
			print(f"Retrying in {RETRY_IN} seconds...")
			self.failed_reads += 1
			await asyncio.sleep(RETRY_IN)
			return await self.read()
		finally:
			if self.failed_reads > MAX_FAILED_ATTEMPTS:
				print(f'Reached maximum number({MAX_FAILED_ATTEMPTS}) of failed attempts. Retrying to connect.')
				self.serial_port.close()
				await self.connect_to_serial()
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


class Readers:
	sensors: List[Sensor]
	relays: List[Relays]
	__current_value: asyncio.Future = asyncio.Future()

	def __init__(self):
		self.__running: bool = False
		self.serial_port: SerialPortWrapper = SerialPortWrapper()

	async def setup(self):
		self.sensors = get_db().query(Sensor).all()
		self.relays = get_db().query(Relays).all()
		self.__running = await self.serial_port.connect_to_serial()

	@classmethod
	async def _save_db(cls, data: List[dict]):
		db = get_db()
		recorded_at = datetime.now().replace(second=0, microsecond=0)
		for item in data:
			if not item.get('temperature'):
				return
			instance: Optional[Temperature] = db.query(Temperature).filter_by(sensor_id=item['sensor_id'], recorded_at=recorded_at).one_or_none()
			if instance is None:
				instance = Temperature(sensor_id=item['sensor_id'], temperature=item['temperature'], recorded_at=recorded_at)
				db.add(instance)
				db.commit()

	def _get_sensor(self, pk: int) -> Union[None, Sensor]:
		return next((item for item in self.sensors if item.id == pk and not item.disabled), None)

	def _get_relay(self, pk: int) -> Union[None, Relays]:
		return next((item for item in self.relays if item.id == pk and not item.disabled), None)

	async def _post_process(self, readings: List[dict]):
		if not len(readings):
			return
		for reading in readings:
			slave_sensor = self._get_sensor(reading['sensor_id'])
			if slave_sensor is None or slave_sensor.pair is None:
				continue
			master_sensor = self._get_sensor(slave_sensor.pair)
			if master_sensor is None:
				continue
			sensor_temp = next((item for item in readings if item['sensor_id'] == slave_sensor.id), None)
			pair_sensor_temp = next((item for item in readings if item['sensor_id'] == master_sensor.id), None)
			if sensor_temp is None or pair_sensor_temp is None:
				continue
			delta = abs(sensor_temp['temperature'] - pair_sensor_temp['temperature'])
			relay = self._get_relay(slave_sensor.relay_id)
			if relay is None:
				continue
			if delta > slave_sensor.delta:
				Relay.turn_on(relay.pin)
			else:
				Relay.turn_off(relay.pin)

	@staticmethod
	def _temp_from_rtd(rtd: float, sensor: Sensor) -> float:
		rtd_nominal = sensor.sensor_type
		ref_resistor = 430 * (rtd_nominal / 100)
		rtd /= 32768
		rtd *= ref_resistor
		z1 = -RTD_A
		z2 = RTD_A * RTD_A - (4 * RTD_B)
		z3 = (4 * RTD_B) / rtd_nominal
		z4 = 2 * RTD_B

		temp = z2 + (z3 * rtd)
		temp = (math.sqrt(temp) + z1) / z4

		if temp >= 0:
			return temp

		rtd /= rtd_nominal
		rtd *= 100

		rpoly: float = rtd
		temp = -242.02
		temp += 2.2228 * rpoly
		rpoly *= rtd
		temp += 2.5859e-3 * rpoly
		rpoly *= rtd
		temp -= 4.8260e-6 * rpoly
		rpoly *= rtd
		temp -= 2.8183e-8 * rpoly
		rpoly *= rtd
		temp += 1.5243e-10 * rpoly
		return temp

	async def read_from_stream(self) -> List:
		result = await self.__current_value
		self.__current_value = asyncio.Future()
		return result

	async def _read(self) -> List:
		sensors: List[Sensor] = [item for item in self.sensors if not item.disabled]
		if not len(sensors):
			await asyncio.sleep(2)

		values: List[dict] = await self.serial_port.read()
		if type(values) is str:
			return []
		result = []
		for item in values:
			sensor = next((el for el in sensors if el.pin == item['pin']), None)
			if sensor is None:
				continue
			item['date'] = str(datetime.now())
			item['sensor_id'] = sensor.id
			item['label'] = sensor.label
			item['temperature'] = self._temp_from_rtd(item.get('rtd'), sensor)
			result.append(item)
		return result

	async def run(self):
		while self.__running:
			result = await self._read()
			asyncio.create_task(self._save_db(result))
			asyncio.create_task(self._post_process(result))
			if self.__current_value.done():
				self.__current_value = asyncio.Future()
			self.__current_value.set_result(result)

	# print(*result, sep='\n')

	def stop(self):
		self.__running = False


readers = Readers()


@event.listens_for(Sensor, 'after_insert')
def add_sensor(mapper, db, instance):
	readers.sensors.append(instance)


@event.listens_for(Sensor, 'after_update')
def update_sensor(mapper, db, instance):
	for idx, sensor in enumerate(readers.sensors):
		if sensor.id == instance.id:
			readers.sensors[idx] = instance


@event.listens_for(Sensor, 'after_delete')
def remove_sensor(mapper, db, instance):
	for idx, sensor in enumerate(readers.sensors):
		if sensor.id == instance.id:
			readers.sensors.pop(idx)


@event.listens_for(Relays, 'after_insert')
def add_relay(mapper, db, instance):
	readers.relays.append(instance)


@event.listens_for(Relays, 'after_update')
def update_relay(mapper, db, instance):
	for idx, relay in enumerate(readers.relays):
		if relay.id == instance.id:
			readers.relays[idx] = instance


@event.listens_for(Relays, 'after_delete')
def remove_relay(mapper, db, instance):
	for idx, relay in enumerate(readers.relays):
		if relay.id == instance.id:
			readers.relays.pop(idx)


if __name__ == '__main__':
	ports = list_ports.comports()
	port = ports[0].device if len(ports) else None
	ser = serial.Serial(port, baudrate=BAUD_RATE)
	while True:
		print(ser.readline().decode('Ascii'))
