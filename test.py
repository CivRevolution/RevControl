import asyncio
import websockets
import time
from aiohttp import web

# WebSocket handler
async def echo(websocket, path):
    while True:
        await websocket.send("Hello, Client!")
        await asyncio.sleep(5)

# HTTP handler to serve the HTML file
async def handle(request):
    with open('client.html', 'r') as f:
        return web.Response(text=f.read(), content_type='text/html')

app = web.Application()
app.router.add_get('/', handle)

# Start the WebSocket server
start_server = websockets.serve(echo, "0.0.0.0", 5678)

# Start the HTTP server
web_runner = web.AppRunner(app)
asyncio.get_event_loop().run_until_complete(web_runner.setup())
site = web.TCPSite(web_runner, '0.0.0.0', 8080)
asyncio.get_event_loop().run_until_complete(site.start())

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
