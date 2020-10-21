from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class InputValidator(BaseModel):
	label: str
	pin: int
	disabled: Optional[bool] = False
	fire_on_threshold: Optional[bool] = False


class ResponseValidator(InputValidator):
	id: int
	created_at: datetime
	updated_at: Optional[datetime]

	class Config:
		orm_mode = True
