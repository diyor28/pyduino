from fastapi import APIRouter, Depends

from app.database import get_db, Session
from app.models import Sensor
from app.validators.Sensor import InputValidator, ResponseValidator

router = APIRouter()


@router.get('/sensors')
async def find_sensors(db: Session = Depends(get_db)):
	items = db.query(Sensor).all()
	return items


@router.get('/sensors/{pk}')
async def get_sensor(pk: str, db: Session = Depends(get_db)):
	item = db.query(Sensor).get(pk)
	return item


@router.post('/sensors', response_model=ResponseValidator)
async def create_sensor(data: InputValidator, db: Session = Depends(get_db)):
	instance = Sensor(**data.dict(exclude_unset=True))
	db.add(instance)
	db.commit()
	return instance


@router.patch('/sensors/{pk}', response_model=ResponseValidator)
async def patch_sensor(pk: str, data: InputValidator, db: Session = Depends(get_db)):
	instance = db.query(Sensor).get(pk)
	for key, value in data.dict(exclude_unset=True).items():
		setattr(instance, key, value)
	db.commit()
	return instance


@router.delete('/sensors/{pk}', response_model=ResponseValidator)
async def delete_sensor(pk: str, db: Session = Depends(get_db)):
	instance = db.query(Sensor).get(pk)
	db.delete(instance)
	db.commit()
	return instance
