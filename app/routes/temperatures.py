from fastapi import APIRouter, Depends

from app.database import get_db, Session
from app.models import Sensor
from app.validators.Sensor import InputValidator, ResponseValidator

router = APIRouter()


@router.get('/temperatures')
async def find_temperatures(db: Session = Depends(get_db)):
	items = db.query(Sensor).all()
	return items


@router.get('/temperatures/{pk}')
async def get_temperature(pk: str, db: Session = Depends(get_db)):
	item = db.query(Sensor).get(pk)
	return item
