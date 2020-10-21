from collections import defaultdict
from typing import Callable, Dict, Any, List, Union, Set, Optional

from fastapi import Query, Depends
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Temperature

LOCATIONS_MAP = {'up': 'ТВ-', 'down': 'ТН-', 'boiler': '', 'street': ''}


def parse_date(date: str) -> Union[datetime, None]:
	if not date:
		return
	return datetime.fromisoformat(date[:-1])


def group_by(values: list, func: Callable) -> Dict[Any, list]:
	result = defaultdict(list)
	for value in values:
		result[func(value)].append(value)
	return dict(result)


def group_temps(items, export=False):
	result = []
	for key, values in group_by(list(items), lambda x: x.recorded_at).items():
		item = {}
		for value in sorted(values, key=lambda x: x.sensor.pin):
			if export:
				prefix = LOCATIONS_MAP[value.sensor.location]
				label = prefix + f"{value.sensor.pin} ({value.sensor.label})"
				item[label] = value.temperature
			else:
				item[value.sensor_id] = value.temperature
		item['recorded_at'] = key
		result.append(item)
	return result


def get_temps(db: Session = Depends(get_db),
			  skip: Optional[int] = Query(None),
			  limit: Optional[int] = Query(None),
			  sensor_ids: Set[int] = Query(None),
			  start_date: str = Query(None),
			  end_date: str = Query(None),
			  export=False):
	items = db.query(Temperature).order_by(desc(Temperature.recorded_at))
	start_date = parse_date(start_date)
	end_date = parse_date(end_date)
	if start_date:
		items = items.filter(Temperature.recorded_at > start_date)
	if end_date:
		items = items.filter(Temperature.recorded_at <= end_date)

	all_sensor_ids = {temp.sensor_id for temp in items.group_by(Temperature.sensor_id).all()}
	if sensor_ids:
		all_sensor_ids.intersection_update(sensor_ids)
	items = items.filter(Temperature.sensor_id.in_(all_sensor_ids))
	count = items.count()
	if skip or limit:
		skip *= len(all_sensor_ids)
		limit *= len(all_sensor_ids)
		result = group_temps(items.offset(skip).limit(limit).all())
		return {'total': count / len(all_sensor_ids), 'data': result}
	return group_temps(items.all(), export=export)
