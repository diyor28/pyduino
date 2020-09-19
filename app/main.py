import asyncio

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.serial_ports import readers
from app.routes import spis, relays, temperatures

app = FastAPI()
app.include_router(spis)
app.include_router(relays)
app.include_router(temperatures)

origins = ["*"]

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event('startup')
async def run_reader():
	asyncio.create_task(readers.setup())
	asyncio.create_task(readers.run())


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
	await websocket.accept()
	while True:
		data = readers.read_from_stream()
		await asyncio.sleep(0.5)
		await websocket.send_json(data)
