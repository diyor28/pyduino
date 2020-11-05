from app.main import app
from app.models import Sensor, Relays, House
from app.database import get_db
import random

# 1 (4, 10)
# 2 (4, 10)
# 3 (1, 4)

HIGH_THRESHOLD = 27
LOW_THRESHOLD = 22

houses = [
	{
		'label': 'Теплица 1',
		'sensors': [
			{'up': 2, 'down': [11, 12], 'relay': 8},
			{'up': 3, 'down': [13, 22], 'relay': 10},
			{'up': 4, 'down': [23, 24, 25], 'relay': 11},
			{'up': 5, 'down': [26, 27, 28], 'relay': 12}
		]
	},
	{
		'label': 'Теплица 2',
		'sensors': [
			{'up': 6, 'down': [29, 30], 'relay': 13},
			{'up': 7, 'down': [31, 32], 'relay': 15},
			{'up': 8, 'down': [33, 34, 35], 'relay': 16},
			{'up': 9, 'down': [36, 37, 38], 'relay': 18}
		]
	},
	{
		'label': 'Теплица 3',
		'sensors': [
			{'up': 10, 'down': [39, 40, 41, 42]}
		]
	}
]

if __name__ == '__main__':
	db = get_db()

	for house in houses:
		house_instance = House(label=house['label'])
		db.add(house_instance)
		db.commit()
		for sensor in house['sensors']:
			up_sensor = Sensor(pin=sensor['up'],
							   sensor_type=1000,
							   location='up',
							   house_id=house_instance.id,
							   high_threshold=HIGH_THRESHOLD,
							   low_threshold=LOW_THRESHOLD)
			db.add(up_sensor)
			db.commit()
			relay_id = None
			if sensor.get('relay'):
				relay = Relays(label='Реле ' + str(sensor['relay']), pin=sensor['relay'])
				db.add(relay)
				db.commit()
				relay_id = relay.id
			for down_pin in sensor['down']:
				db.add(Sensor(pin=down_pin,
							  sensor_type=1000,
							  pair=up_sensor.id,
							  house_id=house_instance.id,
							  high_threshold=HIGH_THRESHOLD,
							  low_threshold=LOW_THRESHOLD,
							  delta=3,
							  location='down',
							  relay_id=relay_id))
				db.commit()

	db.add(Sensor(sensor_type=1000, pin=43, location='boiler', label='Котельная'))
	db.add(Sensor(sensor_type=1000, pin=44, location='street', label='Улица'))
	db.commit()
