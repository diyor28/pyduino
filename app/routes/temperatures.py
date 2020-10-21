from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.validators.Temperature import ResponseValidator
from app.helpers import get_temps

router = APIRouter()


class PaginatedResponse(BaseModel):
	total: int
	data: List[ResponseValidator]


# noinspection PyTypeChecker
@router.get('/temperatures')
async def find_temperatures(result=Depends(get_temps)):
	return result
