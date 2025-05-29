import uvicorn
import asyncio
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from deploy import deploy_all, running_bots

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(deploy_all())

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "bots": list(running_bots.keys())
    })

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080)
