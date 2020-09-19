import json
import asyncio
import time
import math
from datetime import datetime
from typing import List, Optional, Dict
import aioserial
import serial
from aioserial import AioSerial
from serial.tools import list_ports
from sqlalchemy import event
from app.database import get_db
from app.models import Sensor, Temperature

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
	failed_write_reads: int = 0

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

	@time_it
	async def read_temp(self, sensor: Sensor) -> dict:
		try:
			await self.serial_port.write_async(json.dumps({'pin': sensor.pin, 'sensor_type': sensor.sensor_type}).encode('Ascii'))
			message: str = (await self.serial_port.readline_async()).decode('Ascii')
		except serial.SerialException as e:
			print(e, self.serial_port.port)
			self.failed_write_reads += 1
			if self.failed_write_reads > 4:
				await self.connect_to_serial()
			await asyncio.sleep(2)
			return await self.read_temp(sensor)
		try:
			print('message:', message)
			data = json.loads(message)
			data['temperature'] = self.temp_from_rtd(data['rtd'], sensor)
			print(data)
		except json.decoder.JSONDecodeError:
			data = {'error': message}
		self.failed_write_reads = 1
		data['date'] = str(datetime.now())
		data['pin'] = sensor.pin
		data['sensor_id'] = sensor.id
		data['label'] = sensor.label
		return data


class Readers:
	sensors: List[Sensor]
	__current_value: Dict[int, dict] = {}

	def __init__(self):
		self.__running: bool = False
		self.serial_port: SerialPortWrapper = SerialPortWrapper()

	async def setup(self):
		self.sensors = get_db().query(Sensor).all()
		self.__running = await self.serial_port.connect_to_serial()

	@classmethod
	async def save_db(cls, data: dict, sensor: Sensor):
		if not data.get('temperature'):
			return
		db = get_db()
		recorded_at = datetime.now().replace(second=0, microsecond=0)
		instance: Optional[Temperature] = db.query(Temperature).filter_by(sensor_id=sensor.id, recorded_at=recorded_at).one_or_none()
		if instance is None:
			instance = Temperature(sensor_id=sensor.id, temperature=data['temperature'], recorded_at=recorded_at)
			db.add(instance)
			db.commit()

	def read_from_stream(self) -> Dict[int, dict]:
		return self.__current_value

	async def run(self):
		while self.__running:
			values = {}
			sensors = list(filter(lambda x: not x.disabled, self.sensors))
			if not len(sensors):
				await asyncio.sleep(2)
			for spi in sensors:
				data = await self.serial_port.read_temp(spi)
				asyncio.create_task(self.save_db(data, spi))
				values[spi.id] = data
			self.__current_value = values

	def stop(self):
		self.__running = False


readers = Readers()


@event.listens_for(Sensor, 'after_insert')
def add_spi(mapper, db, instance):
	readers.sensors.append(instance)


@event.listens_for(Sensor, 'after_update')
def update_spi(mapper, db, instance):
	for idx, spi in enumerate(readers.sensors):
		if spi.id == instance.id:
			readers.sensors[idx] = instance


@event.listens_for(Sensor, 'after_delete')
def remove_spi(mapper, db, instance):
	for idx, spi in enumerate(readers.sensors):
		if spi.id == instance.id:
			readers.sensors.pop(idx)


if __name__ == '__main__':
	ser = serial.Serial('COM6', baudrate=BAUD_RATE)
	while True:
		print(ser.readline().decode('Ascii'))
