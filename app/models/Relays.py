from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from datetime import datetime

from app.database import Base


class Relays(Base):
	__tablename__ = "relays"

	id = Column(Integer, primary_key=True, index=True)
	label = Column(String)
	pin = Column(Integer, unique=True, index=True)
	disabled = Column(Boolean, default=False)
	created_at = Column(DateTime, default=datetime.now)
	updated_at = Column(DateTime, onupdate=datetime.now)
