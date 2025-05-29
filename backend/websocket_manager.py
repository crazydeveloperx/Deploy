import asyncio, os
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, bot_id: str):
        await websocket.accept()
        self.active_connections[bot_id] = websocket

    async def disconnect(self, websocket: WebSocket):
        for bot_id, ws in list(self.active_connections.items()):
            if ws == websocket:
                del self.active_connections[bot_id]

    async def stream_logs(self, bot_id: str, log_file: str):
        pos = 0
        while bot_id in self.active_connections:
            if os.path.exists(log_file):
                with open(log_file) as f:
                    f.seek(pos)
                    data = f.read()
                    pos = f.tell()
                    if data:
                        try:
                            await self.active_connections[bot_id].send_text(data)
                        except:
                            break
            await asyncio.sleep(1)

manager = WebSocketManager()
