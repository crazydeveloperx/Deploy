import os, asyncio, subprocess, uuid
from backend.bot_registry import save_bot, update_bot_status
from backend.websocket_manager import manager

async def deploy_bot(details):
    bot_id = str(uuid.uuid4())
    folder = f"bots/{bot_id}"
    log_file = f"logs/{bot_id}.log"
    os.makedirs(folder, exist_ok=True)

    with open(log_file, "w") as f:
        f.write("Starting deployment...\n")

    git_url = f"https://{details.token}@github.com/{details.github_username}/{details.repo_name}.git"
    clone_cmd = ["git", "clone", "-b", details.branch, git_url, folder]

    proc = await asyncio.create_subprocess_exec(*clone_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    with open(log_file, "a") as f:
        f.write(stdout.decode() + stderr.decode())

    if proc.returncode != 0:
        await update_bot_status(bot_id, "failed")
        return

    entry_file_path = os.path.join(folder, details.entry_file)
    bot_process = subprocess.Popen(["python3", entry_file_path], stdout=open(log_file, "a"), stderr=subprocess.STDOUT)

    await save_bot(bot_id, details, bot_process.pid, log_file)
    await update_bot_status(bot_id, "running")
    asyncio.create_task(manager.stream_logs(bot_id, log_file))
