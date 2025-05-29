from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Constants
MONGO_URL = "mongodb+srv://User2:User2@cluster0.77jdwye.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "crazy"

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URL)   # ✅ Pass the variable, not the string
db = client[DB_NAME]                     # ✅ Use indexing, not parentheses
bots = db["bots"]

# Save a bot document
async def save_bot(bot_id, details, pid, log_file):
    data = {
        "_id": bot_id,
        "github_username": details.github_username,
        "repo_name": details.repo_name,
        "branch": details.branch,
        "entry_file": details.entry_file,
        "status": "starting",
        "pid": pid,
        "log_file": log_file,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await bots.insert_one(data)

# Update a bot's status
async def update_bot_status(bot_id, status):
    await bots.update_one(
        {"_id": bot_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
