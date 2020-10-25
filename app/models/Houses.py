from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from app.database import Base


class House(Base):
	__tablename__ = "houses"

	id = Column(Integer, primary_key=True, index=True)
	label = Column(String)
	created_at = Column(DateTime, default=datetime.now)
	updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
