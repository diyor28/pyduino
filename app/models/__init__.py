from .Temperature import Temperature
from .Relays import Relays
from .Download import Download
from .Houses import House
from .Sensor import Sensor
from .Sensor import Base

from app.database import engine

Base.metadata.create_all(bind=engine)
