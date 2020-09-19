import json
import asyncio
import time
import math
from datetime import datetime
from typing import List, Optional, Dict, Union
import aioserial
import serial
from aioserial import AioSerial
from serial.tools import list_ports
from sqlalchemy import event
from app.database import get_db
from app.models import Sensor, Temperature
from app.gpio import Relay

RTD_A = 3.9083e-3
RTD_B = - 5.775e-7
BAUD_RATE = 250_000


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

	def __init__(self):
		pass

	async def connect_to_serial(self):
		ports = list_ports.comports()
		port = ports[0].device if len(ports) else None
		if port is None:
			print("Could not find any serial device. Retrying in 2 seconds...")
			await asyncio.sleep(2)
			await self.connect_to_serial()
		try:
			self.serial_port: AioSerial = AioSerial(port=port, baudrate=BAUD_RATE, bytesize=8, timeout=2, stopbits=aioserial.STOPBITS_ONE)
		except serial.SerialException as e:
			print(e)
			await asyncio.sleep(2)
			await self.connect_to_serial()
		return True

	@time_it
	async def read(self) -> Union[List[dict], str]:
		try:
			message: str = (await self.serial_port.readline_async()).decode('Ascii')
		except serial.SerialException as e:
			print(e, self.serial_port.port)
			self.failed_reads += 1
			if self.failed_reads > 4:
				await self.connect_to_serial()
			await asyncio.sleep(2)
			return await self.read()
		try:
			result = json.loads(message)
			if type(result) is not list:
				return message
		except json.decoder.JSONDecodeError:
			return message
		self.failed_reads = 0
		return result


class Readers:
	sensors: List[Sensor]
	__current_value: List[dict] = []

	def __init__(self):
		self.__running: bool = False
		self.serial_port: SerialPortWrapper = SerialPortWrapper()

	async def setup(self):
		self.sensors = get_db().query(Sensor).all()
		self.__running = await self.serial_port.connect_to_serial()

	@classmethod
	async def save_db(cls, data: List[dict]):
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

	def read_from_stream(self) -> List:
		return self.__current_value

	@staticmethod
	def get_sensor(sensors: List[Sensor], pk: int) -> Union[None, Sensor]:
		sensor = [item for item in sensors if item.id == pk]
		if not len(sensor):
			return
		return sensor[0]

	async def post_process(self, readings: List[dict]):
		if not len(readings):
			return
		sensors: List[Sensor] = [item for item in self.sensors if not item.disabled]
		for reading in readings:
			sensor = self.get_sensor(sensors, reading['sensor_id'])
			if sensor is None:
				continue
			pair_sensor = self.get_sensor(sensors, sensor.pair)
			if pair_sensor is None:
				continue
			sensor_temp = next((item for item in readings if item['sensor_id'] == sensor.id), None)
			pair_sensor_temp = next((item for item in readings if item['sensor_id'] == pair_sensor.id), None)
			delta = abs(sensor_temp['temperature'] - pair_sensor_temp['temperature'])
			print(delta, sensor.label, pair_sensor.label)
			if delta > sensor.delta:
				Relay(8).fire()
				print('FIRING RELAY')

	@staticmethod
	def temp_from_rtd(rtd: float, sensor: Sensor) -> float:
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

	async def run(self):
		while self.__running:
			sensors: List[Sensor] = [item for item in self.sensors if not item.disabled]
			if not len(sensors):
				await asyncio.sleep(2)
			values: List[dict] = await self.serial_port.read()
			if type(values) is str:
				print(str)
				continue
			result = []
			for item in values:
				sensor = next((el for el in sensors if el.pin == item['pin']), None)
				if sensor is None:
					continue
				item['date'] = str(datetime.now())
				item['sensor_id'] = sensor.id
				item['label'] = sensor.label
				item['temperature'] = self.temp_from_rtd(item.get('rtd'), sensor)
				result.append(item)
			asyncio.create_task(self.save_db(result))
			print(*result, sep='\n')
			asyncio.create_task(self.post_process(result))
			self.__current_value = result

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


if __name__ == '__main__':
	ports = list_ports.comports()
	port = ports[0].device if len(ports) else None
	ser = serial.Serial(port, baudrate=BAUD_RATE)
	while True:
		print(ser.readline().decode('Ascii'))
