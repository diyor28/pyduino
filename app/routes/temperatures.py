from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc

from typing import List, Dict, Optional
from pydantic import BaseModel
from app.database import get_db, Session
from fastapi.responses import FileResponse
from app.models import Temperature, Sensor
from app.validators.Temperature import InputValidator, ResponseValidator

router = APIRouter()


class DownloadValidator(BaseModel):
	sensor_id: Optional[int]


# noinspection PyTypeChecker
@router.get('/temperatures', response_model=List[ResponseValidator])
async def find_temperatures(db: Session = Depends(get_db), sensor_id: str = Query(None)):
	items = db.query(Temperature)
	if sensor_id:
		items = items.filter_by(sensor_id=sensor_id)
	return items.order_by(desc(Temperature.recorded_at)).all()


@router.get('/download')
async def get_export(data: DownloadValidator, db: Session = Depends(get_db)):
	items = db.query(Temperature)
	items = items.filter_by(**data.dict(exclude_unset=True))
	return FileResponse()
