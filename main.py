from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import subprocess
import os
import shutil
import uuid
import signal
from database import SessionLocal, engine
from models import Base, BotDeployment
from schemas import BotCreate, BotStatus
from utils import clone_repo, start_bot_process, stop_bot_process

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

class LogManager:
    def __init__(self):
        self.connections = {}
        self.log_queues = {}

    async def push_log(self, bot_id: str, message: str):
        if bot_id in self.log_queues:
            self.log_queues[bot_id].append(message)
        for websocket in self.connections.get(bot_id, []):
            await websocket.send_text(message)

    async def connect(self, websocket: WebSocket, bot_id: str):
        await websocket.accept()
        if bot_id not in self.connections:
            self.connections[bot_id] = []
            self.log_queues[bot_id] = []
        self.connections[bot_id].append(websocket)

    def disconnect(self, websocket: WebSocket, bot_id: str):
        if bot_id in self.connections:
            self.connections[bot_id].remove(websocket)

log_manager = LogManager()

@app.post("/deploy/")
async def deploy_bot(bot_data: BotCreate):
    db = SessionLocal()
    bot_id = str(uuid.uuid4())
    clone_dir = f"clones/{bot_id}"
    log_file = f"logs/{bot_id}.log"
    
    bot_deployment = BotDeployment(
        id=bot_id,
        name=bot_data.name or bot_data.repo_name,
        github_username=bot_data.github_username,
        repo_name=bot_data.repo_name,
        branch=bot_data.branch or "main",
        entry_file=bot_data.entry_file or "bot.py",
        status="deploying",
        log_file=log_file
    )
    
    try:
        db.add(bot_deployment)
        db.commit()
        db.refresh(bot_deployment)
        
        # Start deployment in background
        asyncio.create_task(run_deployment(bot_deployment, clone_dir, log_file))
        
        return {"id": bot_id, "message": "Deployment started"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

async def run_deployment(bot: BotDeployment, clone_dir: str, log_file: str):
    db = SessionLocal()
    try:
        await log_manager.push_log(bot.id, "🔍 Starting deployment...")
        
        # Clone repository
        await clone_repo(
            bot.github_username,
            bot.repo_name,
            bot.branch,
            clone_dir,
            log_manager,
            bot.id
        )
        
        # Start bot process
        pid = await start_bot_process(
            clone_dir,
            bot.entry_file,
            log_file,
            log_manager,
            bot.id
        )
        
        # Update database
        bot.status = "running"
        bot.pid = pid
        db.commit()
        await log_manager.push_log(bot.id, f"✅ Bot is running (PID: {pid})")
        
    except Exception as e:
        bot.status = "failed"
        db.commit()
        await log_manager.push_log(bot.id, f"❌ Deployment failed: {str(e)}")
    finally:
        db.close()

@app.get("/bots/", response_model=list[BotStatus])
def list_bots():
    db = SessionLocal()
    bots = db.query(BotDeployment).all()
    db.close()
    return bots

@app.delete("/bots/{bot_id}")
def delete_bot(bot_id: str):
    db = SessionLocal()
    bot = db.query(BotDeployment).filter(BotDeployment.id == bot_id).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    try:
        # Stop bot process
        if bot.pid:
            stop_bot_process(bot.pid)
        
        # Remove clone directory
        clone_dir = f"clones/{bot_id}"
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
        
        # Remove log file
        if os.path.exists(bot.log_file):
            os.remove(bot.log_file)
        
        # Delete database record
        db.delete(bot)
        db.commit()
        return {"message": "Bot deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.websocket("/logs/{bot_id}")
async def websocket_logs(websocket: WebSocket, bot_id: str):
    await log_manager.connect(websocket, bot_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(websocket, bot_id)
