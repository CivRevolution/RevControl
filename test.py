import asyncio
import websockets
import time

async def echo(websocket, path):
    while True:
        await websocket.send("Hello, Client!")
        await asyncio.sleep(5)

start_server = websockets.serve(echo, "0.0.0.0", 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
