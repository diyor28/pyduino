import asyncio
import math
from datetime import datetime
from typing import List, Optional, Union, Tuple

import serial
from serial.tools import list_ports
from sqlalchemy import event, desc

from app.database import get_db
from app.models import Sensor, Temperature, Relays
from app.gpio import Relay
from app.settings import DEBUG, BAUD_RATE, RTD_A, RTD_B, RETRY_IN
from app.serial_ports import SerialPortWrapper


class Readers:
	sensors: List[Sensor] = []
	relays: List[Relays] = []
	__value_promise: asyncio.Future = asyncio.Future()
	__error_message: str
	__running: bool = True
	__current_value: List[dict] = []

	def __init__(self):
		self.db = get_db()
		self.serial_port: SerialPortWrapper = SerialPortWrapper()

	async def setup(self):
		self.sensors = self.db.query(Sensor).order_by(desc(Sensor.pin)).all()
		self.relays = self.db.query(Relays).all()
		await self.serial_port.connect_to_serial()
		asyncio.create_task(self.run())

	async def _save_db(self, data: List[dict]):
		date = datetime.utcnow()
		recorded_at = date.replace(second=0, microsecond=0, minute=date.minute)
		for item in data:
			if not item.get('temperature'):
				return
			instance: Optional[Temperature] = self.db.query(Temperature).filter_by(sensor_id=item['sensor_id'], recorded_at=recorded_at).one_or_none()
			if instance is None:
				instance = Temperature(sensor_id=item['sensor_id'], temperature=item['temperature'], recorded_at=recorded_at)
				self.db.add(instance)
				self.db.commit()

	def _get_sensor(self, pk: int) -> Union[None, Sensor]:
		return next((item for item in self.sensors if item.id == pk and not item.disabled), None)

	def _get_relay(self, pk: int) -> Union[None, Relays]:
		return next((item for item in self.relays if item.id == pk and not item.disabled), None)

	def _get_threshold_relay(self):
		return next((item for item in self.relays if item.fire_on_threshold), None)

	async def _post_process(self, readings: List[dict]):
		if not len(readings):
			return

		threshold_hit = []
		for sensor_reading in readings:
			slave_sensor = self._get_sensor(sensor_reading['sensor_id'])

			if not slave_sensor:
				continue

			if slave_sensor.high_threshold:
				threshold_hit.append(sensor_reading['temperature'] > slave_sensor.high_threshold)

			if slave_sensor.low_threshold:
				threshold_hit.append(sensor_reading['temperature'] < slave_sensor.low_threshold)

			master_sensor = self._get_sensor(slave_sensor.pair)
			if master_sensor is None:
				continue

			pair_sensor_temp = next((item for item in readings if item['sensor_id'] == master_sensor.id), None)
			if not pair_sensor_temp:
				continue

			delta = abs(sensor_reading['temperature'] - pair_sensor_temp['temperature'])
			relay = self._get_relay(slave_sensor.relay_id)

			if relay is None:
				continue

			if delta > slave_sensor.delta:
				Relay.turn_on(relay.pin)
			else:
				Relay.turn_off(relay.pin)

		threshold_relay = self._get_threshold_relay()

		if not threshold_relay:
			return

		if threshold_relay.disabled:
			Relay.turn_off(threshold_relay.pin)
			return

		if any(threshold_hit):
			Relay.turn_on(threshold_relay.pin)
		else:
			Relay.turn_off(threshold_relay.pin)

	@staticmethod
	def _temp_from_rtd(rtd: float, sensor: Sensor) -> float:
		rtd_nominal = sensor.sensor_type
		resistance = Readers._resistance_from_rtd(rtd, sensor)
		z1 = -RTD_A
		z2 = RTD_A * RTD_A - (4 * RTD_B)
		z3 = (4 * RTD_B) / rtd_nominal
		z4 = 2 * RTD_B

		temp = z2 + (z3 * resistance)
		temp = (math.sqrt(temp) + z1) / z4

		return round(temp, 1)

	@staticmethod
	def _resistance_from_temp(temperature: float, sensor: Sensor) -> float:
		rtd_nominal = sensor.sensor_type
		z1 = -RTD_A
		z2 = RTD_A * RTD_A - (4 * RTD_B)
		z3 = (4 * RTD_B) / rtd_nominal
		z4 = 2 * RTD_B
		temperature = (temperature * z4 - z1) ** 2
		resistance = (temperature - z2) / z3
		return resistance

	@staticmethod
	def _resistance_from_rtd(rtd: float, sensor: Sensor):
		ref_resistor = 430 * (sensor.sensor_type / 100)
		wire_resistance = sensor.wire_resistance or 0
		correction_resistance = sensor.correction_resistance or 0
		return ref_resistor * rtd / 32768 + wire_resistance + correction_resistance

	async def _read(self) -> Tuple[List, str]:
		if not self.serial_port.connected:
			await asyncio.sleep(RETRY_IN)
			return [], 'Не возможно подключиться к датчикам'
		sensors: List[Sensor] = [item for item in self.sensors if not item.disabled]
		if not len(sensors):
			await asyncio.sleep(2)
			return [], 'Нет активных датчиков'
		value: List[dict]
		values, self.__error_message = await self.serial_port.read()
		result = []
		for item in values:
			sensor = next((el for el in sensors if el.pin == item['pin']), None)
			if sensor is None:
				continue
			item['date'] = str(datetime.now())
			item['sensor_id'] = sensor.id
			item['label'] = sensor.label
			item['temperature'] = self._temp_from_rtd(item.get('rtd'), sensor)
			item['resistance'] = self._resistance_from_rtd(item.get('rtd'), sensor)
			result.append(item)
		if DEBUG:
			print(*[{item['pin']: [item['temperature'], item['resistance']]} for item in result], sep='\n')
			print('\n' * 2)
		return result, ''

	async def read_from_stream(self) -> Tuple[List, str]:
		result, error_message = await self.__value_promise
		self.__value_promise = asyncio.Future()
		return result, error_message

	async def run(self):
		while self.__running:
			result, error_message = await self._read()
			self.__current_value = result.copy()
			if self.__value_promise.done():
				self.__value_promise = asyncio.Future()
			self.__value_promise.set_result((result, error_message))

			if result:
				asyncio.create_task(self._save_db(result))
				asyncio.create_task(self._post_process(result))

	async def calibrate(self, temperature: float):
		for reading in self.__current_value:
			sensor = self._get_sensor(reading['sensor_id'])
			ref_resistance = self._resistance_from_temp(temperature, sensor)
			correction_resistance = sensor.correction_resistance or 0
			sensor.correction_resistance = round(ref_resistance - (reading['resistance'] - correction_resistance), 2)
		self.db.commit()

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
