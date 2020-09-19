from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey

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
	low_threshold = Column(Float)
	high_threshold = Column(Float)
	delta = Column(Float)
