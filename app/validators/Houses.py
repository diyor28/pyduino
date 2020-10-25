from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class InputValidator(BaseModel):
	label: str


class ResponseValidator(InputValidator):
	id: int
	created_at: datetime
	updated_at: datetime

	class Config:
		orm_mode = True
