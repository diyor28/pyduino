from app.main import app
from app.models import Sensor, Relays, House
from app.database import get_db
import random

up_sensors = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 22, 23, 24, 25, 26, 27]
down_sensors = [28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42]
relay_pins = [8, 10, 12, 11, 13, 15, 16, 18, 22, 29, 31, 32, 33, 36, 37]
houses = [1, 2, 3]

if __name__ == '__main__':
	db = get_db()
	house_instances = []
	for house in houses:
		house_instances.append(House(label='Теплица ' + str(house)))
	db.add_all(house_instances)
	db.commit()

	for up_pin, down_pin, relay_pin in zip(up_sensors, down_sensors, relay_pins):
		print('Adding sensor', up_pin, down_pin, relay_pin)
		up_sensor = Sensor(pin=up_pin, sensor_type=1000, location='up',
						   house_id=random.choice(house_instances).id,
						   high_threshold=25,
						   low_threshold=23)
		db.add(up_sensor)
		relay_id = None
		if relay_pin:
			relay = Relays(label='Сенсор ' + str(down_pin), pin=relay_pin)
			db.add(relay)
			relay_id = relay.id
		db.commit()
		db.add(Sensor(pin=down_pin,
					  sensor_type=1000,
					  pair=up_sensor.id,
					  house_id=up_sensor.house_id,
					  high_threshold=25,
					  low_threshold=23,
					  delta=3,
					  location='down',
					  relay_id=relay_id))
	db.add(Sensor(sensor_type=1000, pin=43, location='boiler', label='Котельная'))
	db.add(Sensor(sensor_type=1000, pin=44, location='street', label='Улица'))
	db.commit()
