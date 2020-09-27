from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class InputValidator(BaseModel):
	label: str
	pin: int
	disabled: Optional[bool]


class ResponseValidator(InputValidator):
	id: str
	created_at: datetime
	updated_at: datetime

	class Config:
		orm_mode = True
