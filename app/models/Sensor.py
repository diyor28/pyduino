from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Sensor(Base):
	__tablename__ = "sensors"

	id = Column(Integer, primary_key=True, index=True)
	label = Column(String)
	sensor_type = Column(Integer, index=True)
	pin = Column(Integer, unique=True, index=True)
	disabled = Column(Boolean, default=False)
	relay_id = Column(Integer, ForeignKey('relays.id', ondelete='CASCADE'))
	location = Column(String)
	pair = Column(Integer)
	wire_resistance = Column(Float, default=0.0)
	correction_resistance = Column(Float, default=0.0)
	low_threshold = Column(Float)
	high_threshold = Column(Float)
	delta = Column(Float)
	temperatures = relationship('Temperature', back_populates="sensor", lazy=True, cascade="all, delete-orphan")
	created_at = Column(DateTime, default=datetime.now)
	updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
