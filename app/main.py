import asyncio

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.serial_ports import readers
from app.routes import spis, relays, temperatures
from app.gpio import GPIO

app = FastAPI()
app.include_router(spis)
app.include_router(relays)
app.include_router(temperatures)

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
	asyncio.create_task(readers.run())


@app.on_event('shutdown')
async def clean_gpio():
	GPIO.cleanup()


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
	await websocket.accept()
	while True:
		data = await readers.read_from_stream()
		try:
			await websocket.send_json(data)
		except Exception as e:
			print(e)
