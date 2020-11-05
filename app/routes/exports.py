import asyncio
import os
import uuid
from typing import List, Union, Dict, Any, Tuple

import pandas as pd
import numpy as np
from pandas.io.formats.style import Styler
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy import func
from fastapi.responses import FileResponse
from xlsxwriter.worksheet import Worksheet

from app.database import get_db, Session
from app.helpers import get_temps
from app.models import Download, House, Sensor
from app.validators.Download import InputValidator, ResponseValidator
from app.settings import BASE_DIR, DOWNLOADS_DIR

router = APIRouter()

colors = ['#a4caff', '#ffebb8', '#f09cff', '#c5fffa', '#9bffb5', '#ecffb2', '#ffa8d5', '#cabeff']


def highlight_cell(temp: dict) -> str:
	if temp is np.nan or type(temp) is not float:
		return ''

	if temp['high_threshold']:
		if temp['temperature'] > temp['high_threshold']:
			return 'color: blue'
	if temp['low_threshold']:
		if temp['temperature'] < temp['low_threshold']:
			return 'color: red'
	return ''


def obj_to_value(temp: dict) -> Union[float, None]:
	if temp is np.nan or type(temp) is not float:
		return temp
	return temp['temperature']


async def save_to_excel(items: List[dict], house_counts: Dict[int, dict], path: str):
	result = pd.ExcelWriter(path)
	df = pd.DataFrame(items).set_index('recorded_at')
	df = df.reindex(df.index.rename('Дата'))
	df = pd.concat([pd.DataFrame([df.columns], index=[1], columns=df.columns), df])
	df = pd.concat([pd.DataFrame([[]], index=[0]), df])
	styling = df.applymap(highlight_cell).copy()
	df = df.applymap(obj_to_value)
	styled: Styler = df.style.apply(lambda x: styling, axis=None)
	styled.to_excel(result, sheet_name='Sheet1')
	sheet: Worksheet = result.sheets['Sheet1']
	first_col = 0
	for index, (house_id, meta_data) in enumerate(house_counts.items()):
		if not meta_data['count']:
			continue
		color = colors[index % len(colors)]
		merge_format = result.book.add_format({
			'align': 'center',
			'valign': 'vcenter',
			'fg_color': color
		})
		house_format = result.book.add_format({'fg_color': color})
		label = meta_data['house'].label if meta_data['house'] else ''
		last_col = meta_data['count'] + first_col - 1
		sheet.merge_range(first_row=1, first_col=first_col,
						  last_row=1, last_col=last_col,
						  data=label, cell_format=merge_format)
		sheet.set_column(first_col=first_col, last_col=last_col, cell_format=house_format)
		first_col += meta_data['count']
	sheet.set_column(0, 0, 30)
	result.save()


@router.get('/exports', response_model=List[ResponseValidator])
async def get_export(db: Session = Depends(get_db)):
	return db.query(Download).order_by(desc(Download.created_at)).all()


@router.post('/exports', response_model=ResponseValidator)
async def create_export(data: InputValidator, db: Session = Depends(get_db)):
	data.dict(exclude_unset=True)
	items = get_temps(db, sensor_ids=data.sensor_ids,
					  start_date=data.start_date,
					  end_date=data.end_date,
					  limit=None,
					  skip=None, export=True)
	if not os.path.exists(os.path.join(BASE_DIR, DOWNLOADS_DIR)):
		os.mkdir(os.path.join(BASE_DIR, DOWNLOADS_DIR))
	file_name = os.path.join(DOWNLOADS_DIR, uuid.uuid4().hex + '.xlsx')
	full_path = os.path.join(BASE_DIR, file_name)
	raw_counts: List[Tuple[Sensor, int]] = db.query(Sensor, func.count(Sensor.house_id)).filter(Sensor.disabled != True).order_by(desc(Sensor.house_id)).group_by(Sensor.house_id).all()
	house_counts: Dict[int, Dict[str, Any]] = {}
	print(full_path)
	for sensor, count in raw_counts:
		house = db.query(House).get(sensor.house_id) if sensor.house_id else None
		house_counts[sensor.house_id] = {'count': count, 'house': house}
	asyncio.create_task(save_to_excel(items, house_counts, full_path))
	instance = Download(label=data.label, filename=file_name)
	db.add(instance)
	db.commit()
	return instance


@router.delete('/exports/{pk}', response_model=ResponseValidator)
async def delete_export(pk: str, db: Session = Depends(get_db)):
	instance: Download = db.query(Download).get(pk)
	db.delete(instance)
	db.commit()
	os.remove(os.path.join(BASE_DIR, instance.filename))
	return instance


@router.get('/download/{pk}/')
async def download_excel(pk: str, db: Session = Depends(get_db)):
	download: Download = db.query(Download).get(pk)
	filename = download.label + '.xlsx'
	return FileResponse(os.path.join(BASE_DIR, download.filename),
						media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
						filename=filename)
