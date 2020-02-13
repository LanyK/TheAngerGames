import asyncio
import json

import websockets

async def hello():
    uri = "ws://localhost:5556"
    async with websockets.connect(uri) as websocket:
        while True:
            await  websocket.send((str.encode(json.dumps({"player1": {"anger": 0.3}, "player2": {"anger": 0.7}}))))
            _ = await websocket.recv()
            await asyncio.sleep(0.5)

asyncio.get_event_loop().run_until_complete(hello())