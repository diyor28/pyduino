from collections import defaultdict
from typing import Callable, Dict, Any, List, Union, Set, Optional, TypedDict

from fastapi import Query, Depends
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Temperature

LOCATIONS_MAP = {'up': 'ТВ', 'down': 'ТН', 'boiler': '', 'street': ''}


class ExportItem(TypedDict):
	temperature: float
	high_threshold: float
	low_threshold: float


def parse_date(date: Optional[str]) -> Union[datetime, None]:
	if not date:
		return
	return datetime.fromisoformat(date[:-1])


def group_by(values: list, func: Callable) -> Dict[Any, list]:
	result = defaultdict(list)
	for value in values:
		result[func(value)].append(value)
	return dict(result)


def group_temps(items: List[Temperature],
				export: bool = False) -> Union[List[Dict[str, ExportItem]], List[Dict[int, float]]]:
	result = []
	key: str
	values: List[Temperature]
	for key, values in group_by(list(items), lambda x: x.recorded_at).items():
		item = {}
		for value in sorted(values, key=lambda x: x.sensor.pin):
			if export:
				prefix = LOCATIONS_MAP[value.sensor.location]
				suffix = f"({value.sensor.label})" if value.sensor.label else ""
				label = f"{prefix}-{value.sensor.pin}" + suffix if prefix else value.sensor.label
				item[label] = {
					'temperature': value.temperature,
					'high_threshold': value.sensor.high_threshold,
					'low_threshold': value.sensor.low_threshold,
					'house_id': value.sensor.house_id
				}
			else:
				item[value.sensor_id] = value.temperature
		if export:
			item = {k: v for k, v in sorted(item.items(), key=lambda x: x[1]['house_id'] or -1, reverse=True)}
		item['recorded_at'] = key
		result.append(item)
	return result


def get_temps(db: Session = Depends(get_db),
			  skip: Optional[int] = Query(None),
			  limit: Optional[int] = Query(None),
			  sensor_ids: Optional[Set[int]] = Query(None),
			  start_date: Optional[str] = Query(None),
			  end_date: Optional[str] = Query(None),
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
		result = group_temps(items.offset(skip).limit(limit).all(), export=export)
		total: int = count // len(all_sensor_ids) if len(all_sensor_ids) else 0
		return {'total': total, 'data': result}
	return group_temps(items.all(), export=export)
