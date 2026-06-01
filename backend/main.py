# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
import os     
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main_agent import main_agent

app = FastAPI()

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


class SendMessageRequest(BaseModel):
    instruction: str


@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    return main_agent(request.instruction)
