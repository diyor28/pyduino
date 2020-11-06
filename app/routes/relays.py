from fastapi import APIRouter, Depends

from app.database import get_db, Session
from app.models import Relays
from app.validators.Relay import InputValidator, ResponseValidator

router = APIRouter()


@router.get('/relays')
async def find_relays(db: Session = Depends(get_db)):
	items = db.query(Relays).all()
	return items


@router.get('/relays/{pk}')
async def get_relay(pk: int, db: Session = Depends(get_db)):
	item = db.query(Relays).get(pk)
	return item


@router.post('/relays', response_model=ResponseValidator)
async def create_relay(data: InputValidator, db: Session = Depends(get_db)):
	instance = Relays(**data.dict(exclude_unset=True))
	db.add(instance)
	db.commit()
	return instance


@router.patch('/relays/{pk}', response_model=ResponseValidator)
async def patch_relay(pk: int, data: InputValidator, db: Session = Depends(get_db)):
	instance = db.query(Relays).get(pk)
	for key, value in data.dict(exclude_unset=True).items():
		setattr(instance, key, value)
	db.commit()
	return instance


@router.delete('/relays/{pk}', response_model=ResponseValidator)
async def delete_relay(pk: int, db: Session = Depends(get_db)):
	instance = db.query(Relays).get(pk)
	db.delete(instance)
	db.commit()
	return instance
