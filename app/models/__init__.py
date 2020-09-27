from .Temperature import Temperature
from .Sensor import Sensor
from .Relays import Relays
from .Download import Download
from .Sensor import Base

from app.database import engine

Base.metadata.create_all(bind=engine)
