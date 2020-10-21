from typing import Optional
from datetime import datetime
from .Sensor import ResponseValidator as SensorValidator
from pydantic import BaseModel


class InputValidator(BaseModel):
	temperature: Optional[float]
	recorded_at: Optional[str]
	sensor_id: Optional[int]
	sensor: Optional[SensorValidator]


class ResponseValidator(InputValidator):
	recorded_at: datetime
	id: int

	class Config:
		orm_mode = True
