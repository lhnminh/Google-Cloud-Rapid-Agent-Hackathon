from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.text_function import generate_ai_text
import os

app = FastAPI()

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


class SendMessageRequest(BaseModel):
    instruction: str


@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    message = generate_ai_text(request.instruction)
    return {"status": "sent", "message": message, "clarification": ""}
