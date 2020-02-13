import asyncio
import random
import websockets
import json

async def anger(websocket, path):
    """
    This is just a dummy server that sends some anger data
    """
    x = 10
    while True:
        await websocket.send(json.dumps({"anger": -(1/x)*10+1}))
        await asyncio.sleep(1)
        x += 1

start_server = websockets.serve(anger,  "127.0.0.1", 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
