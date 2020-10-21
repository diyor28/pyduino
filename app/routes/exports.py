import os
import uuid
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc

from typing import List, Dict, Optional, Union
from pydantic import BaseModel
from app.database import get_db, Session
from fastapi.responses import FileResponse

from app.helpers import get_temps
from app.models import Temperature, Sensor, Download
from app.validators.Download import InputValidator, ResponseValidator
from app.settings import BASE_DIR, DOWNLOADS_DIR

router = APIRouter()


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
	df = pd.DataFrame(items)
	df = df.rename(columns={'recorded_at': 'Дата'})
	print(df.head())
	df.to_excel(full_path)
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
