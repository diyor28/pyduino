from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class InputValidator(BaseModel):
	label: str
	pin: int
	sensor_type: int
	location: str
	disabled: Optional[bool]
	pair: Optional[int]
	relay_id: Optional[int]
	low_threshold: Optional[float]
	high_threshold: Optional[float]
	delta: Optional[float]


class ResponseValidator(InputValidator):
	id: str
	created_at: datetime
	updated_at: datetime

	class Config:
		orm_mode = True
