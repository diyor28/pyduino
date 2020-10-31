import asyncio
import random
from typing import Tuple, List

from app.database import get_db
from app.models import Sensor
from app.settings import RTD_A, RTD_B


def rtd_from_temp(sensor: Sensor, temp: float) -> int:
	rtd_nominal = sensor.sensor_type
	z1 = -RTD_A
	z2 = RTD_A * RTD_A - (4 * RTD_B)
	z3 = (4 * RTD_B) / rtd_nominal
	z4 = 2 * RTD_B
	temperature = (temp * z4 - z1) ** 2
	resistance = (temperature - z2) / z3
	wire_resistance = sensor.wire_resistance or 0
	correction_resistance = sensor.correction_resistance or 0
	ref_resistor = 430 * (sensor.sensor_type / 100)
	rtd = (resistance - correction_resistance - wire_resistance) * 32768 / ref_resistor
	return rtd


class SerialPortWrapper:
	failed_reads: int = 0
	connected: bool = True

	async def read(self) -> Tuple[List[dict], str]:
		data = []
		await asyncio.sleep(1)
		for sensor in get_db().query(Sensor).all():
			temperature = round((22 + random.random() * 3), 1)
			data.append({'pin': sensor.pin, 'rtd': rtd_from_temp(sensor, temperature)})
		return data, ''

	async def connect_to_serial(self):
		return
