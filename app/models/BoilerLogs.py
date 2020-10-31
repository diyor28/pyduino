from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime

from app.database import Base


class BoilerLogs(Base):
	__tablename__ = "boiler_logs"

	id = Column(Integer, primary_key=True, index=True)
	house_id = Column(Integer, ForeignKey('houses.id'))
	start_date = Column(DateTime)
	end_date = Column(DateTime)
	created_at = Column(DateTime, default=datetime.now)
