from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey

from app.database import Base


class Relays(Base):
	__tablename__ = "relays"

	id = Column(Integer, primary_key=True, index=True)
	label = Column(String)
	pin = Column(Integer, unique=True, index=True)
	disabled = Column(Boolean, default=False)
