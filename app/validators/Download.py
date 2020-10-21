from typing import Optional, List, Set
from datetime import datetime
from pydantic import BaseModel


class InputValidator(BaseModel):
	label: str
	start_date: Optional[str]
	end_date: Optional[str]
	sensor_ids: Optional[Set[int]]


class ResponseValidator(BaseModel):
	id: int
	label: str
	filename: str
	created_at: datetime

	class Config:
		orm_mode = True
