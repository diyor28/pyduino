from typing import Optional

from pydantic import BaseModel


class InputValidator(BaseModel):
	label: str
	pin: int
	disabled: Optional[bool]


class ResponseValidator(InputValidator):
	id: str

	class Config:
		orm_mode = True
