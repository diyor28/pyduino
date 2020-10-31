import os
from typing import List, Tuple, Dict, Any
import uuid
import asyncio

from sqlalchemy import desc, func

from app.helpers import get_temps
from app.models import House, Sensor
from app.database import get_db
from app.settings import BASE_DIR, DOWNLOADS_DIR
from app.routes.exports import save_to_excel

db = get_db()
items = get_temps(db, sensor_ids=None,
				  start_date=None,
				  end_date=None,
				  limit=None,
				  skip=None, export=True)

if not os.path.exists(os.path.join(BASE_DIR, DOWNLOADS_DIR)):
	os.mkdir(os.path.join(BASE_DIR, DOWNLOADS_DIR))
file_name = os.path.join(DOWNLOADS_DIR, 'test.xlsx')
full_path = os.path.join(BASE_DIR, file_name)

raw_counts: List[Tuple[Sensor, int]] = db.query(Sensor, func.count(Sensor.house_id)).filter(Sensor.disabled != True).order_by(desc(Sensor.house_id)).group_by(Sensor.house_id).all()
house_counts: Dict[int, Dict[str, Any]] = {}

for sensor, count in raw_counts:
	house = db.query(House).get(sensor.house_id) if sensor.house_id else None
	house_counts[sensor.house_id] = {'count': count, 'house': house}

asyncio.run(save_to_excel(items, house_counts, full_path))
