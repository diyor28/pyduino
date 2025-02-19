import asyncio
from typing import Union, List

from fastapi import APIRouter, Depends

from app.database import get_db, Session
from app.models import Sensor
from app.validators.Sensor import InputValidator, PatchValidator, ResponseValidator

router = APIRouter()


async def patch_pair_sensor(db: Session, instance: Sensor):
	pair_sensors: Union[List[Sensor], None] = db.query(Sensor).filter(Sensor.pair == instance.id).all()
	if not pair_sensors:
		return
	for pair_sensor in pair_sensors:
		pair_sensor.house_id = instance.house_id
	db.commit()


@router.get('/sensors')
async def find_sensors(db: Session = Depends(get_db)):
	items = db.query(Sensor).all()
	for item in items:
		item.count = db.query(Sensor).filter(Sensor.pair == item.id).count()
	return items


@router.get('/sensors/{pk}')
async def get_sensor(pk: int, db: Session = Depends(get_db)):
	item = db.query(Sensor).get(pk)
	item.count = db.query(Sensor).filter(Sensor.pair == item.id).count()
	return item


@router.post('/sensors', response_model=ResponseValidator)
async def create_sensor(data: InputValidator, db: Session = Depends(get_db)):
	instance = Sensor(**data.dict(exclude_unset=True))
	db.add(instance)
	db.commit()
	asyncio.create_task(patch_pair_sensor(db, instance))
	return instance


@router.patch('/sensors/{pk}', response_model=ResponseValidator)
async def patch_sensor(pk: int, data: PatchValidator, db: Session = Depends(get_db)):
	instance = db.query(Sensor).get(pk)
	for key, value in data.dict(exclude_unset=True).items():
		setattr(instance, key, value)
	db.commit()
	print(data.dict(exclude_unset=True))
	asyncio.create_task(patch_pair_sensor(db, instance))
	return instance


@router.delete('/sensors/{pk}', response_model=ResponseValidator)
async def delete_sensor(pk: int, db: Session = Depends(get_db)):
	instance = db.query(Sensor).get(pk)
	db.delete(instance)
	db.commit()
	return instance
