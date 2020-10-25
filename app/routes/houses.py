from fastapi import APIRouter, Depends

from app.database import get_db, Session
from app.models import House
from app.validators.Houses import InputValidator, ResponseValidator

router = APIRouter()


@router.get('/houses')
async def find_houses(db: Session = Depends(get_db)):
	items = db.query(House).all()
	return items


@router.get('/houses/{pk}')
async def get_sensor(pk: str, db: Session = Depends(get_db)):
	item = db.query(House).get(pk)
	return item


@router.post('/houses', response_model=ResponseValidator)
async def create_sensor(data: InputValidator, db: Session = Depends(get_db)):
	instance = House(**data.dict(exclude_unset=True))
	db.add(instance)
	db.commit()
	return instance


@router.patch('/houses/{pk}', response_model=ResponseValidator)
async def patch_sensor(pk: str, data: InputValidator, db: Session = Depends(get_db)):
	instance = db.query(House).get(pk)
	for key, value in data.dict(exclude_unset=True).items():
		setattr(instance, key, value)
	db.commit()
	return instance


@router.delete('/houses/{pk}', response_model=ResponseValidator)
async def delete_sensor(pk: str, db: Session = Depends(get_db)):
	instance = db.query(House).get(pk)
	db.delete(instance)
	db.commit()
	return instance
