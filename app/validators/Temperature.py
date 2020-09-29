from typing import Optional
from datetime import datetime
from .Sensor import ResponseValidator as SensorValidator
from pydantic import BaseModel


class InputValidator(BaseModel):
	temperature: float
	recorded_at: str
	sensor_id: int
	sensor: Optional[SensorValidator]


class ResponseValidator(InputValidator):
	recorded_at: datetime
	id: str

	class Config:
		orm_mode = True
