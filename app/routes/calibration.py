from fastapi import APIRouter

from app.validators.Calibration import InputValidator
from app.processing import readers

router = APIRouter()


@router.post('/calibration')
async def calibrate(data: InputValidator):
	await readers.calibrate(data.temperature)
