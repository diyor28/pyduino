from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from app.database import Base


class Temperature(Base):
	__tablename__ = "temperature"

	id = Column(Integer, primary_key=True, index=True)
	temperature = Column(Float)
	recorded_at = Column(DateTime, index=True)
	sensor_id = Column(Integer, ForeignKey('sensors.id', ondelete='CASCADE'))
