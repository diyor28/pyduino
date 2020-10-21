import asyncio

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.processing import readers
from app.routes import spis, relays, temperatures, exports, calibration
from app.models import Sensor
from app.gpio import GPIO
from app.database import get_db

app = FastAPI()
app.include_router(spis)
app.include_router(relays)
app.include_router(temperatures)
app.include_router(exports)
app.include_router(calibration)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event('startup')
async def run_reader():
	asyncio.create_task(readers.setup())


@app.on_event('shutdown')
async def clean_gpio():
	GPIO.cleanup()


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
	await websocket.accept()
	while True:
		data, err = await readers.read_from_stream()
		# data = [{'sensor_id': sensor.id, 'temperature': 27.53, 'pair': sensor.pair, 'relay_id': sensor.relay_id}
		# 		for sensor in get_db().query(Sensor).all()]
		try:
			await websocket.send_json({'data': data, 'err': err})
		except Exception as e:
			print(e)
