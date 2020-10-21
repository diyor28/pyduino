from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database import Base


class Download(Base):
	__tablename__ = "downloads"

	id = Column(Integer, primary_key=True, index=True)
	label = Column(String)
	filename = Column(String)
	created_at = Column(DateTime, default=datetime.now)
