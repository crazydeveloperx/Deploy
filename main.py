from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from deploy_manager import deploy_bot
from websocket_manager import manager
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class BotDetails(BaseModel):
    github_username: str
    repo_name: str
    branch: str = "main"
    entry_file: str = "bot.py"
    token: str

@app.post("/deploy")
async def deploy(details: BotDetails, background_tasks: BackgroundTasks):
    background_tasks.add_task(deploy_bot, details)
    return {"message": "Deployment started"}

@app.websocket("/ws/logs/{bot_id}")
async def websocket_logs(websocket: WebSocket, bot_id: str):
    await manager.connect(websocket, bot_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await manager.disconnect(websocket)
