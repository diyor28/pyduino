from .Temperature import Temperature
from .Relays import Relays
from .Download import Download
from .House import House
from .Sensor import Sensor
from .BoilerLogs import BoilerLogs
from .Sensor import Base

from app.database import engine

Base.metadata.create_all(bind=engine)
