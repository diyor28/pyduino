from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class InputValidator(BaseModel):
	label: Optional[str]
	pin: int
	sensor_type: int
	location: str
	wire_resistance: Optional[float]
	disabled: Optional[bool]
	pair: Optional[int]
	relay_id: Optional[int]
	correction_resistance: Optional[float]
	low_threshold: Optional[float]
	high_threshold: Optional[float]
	delta: Optional[float]


class PatchValidator(InputValidator):
	pin: Optional[int]
	sensor_type: Optional[int]
	location: Optional[str]


class ResponseValidator(InputValidator):
	id: int
	created_at: datetime
	updated_at: datetime

	class Config:
		orm_mode = True
