from fastapi import FastAPI
from pydantic import BaseModel
from backend.text_function import generate_ai_text

app = FastAPI()


class SendMessageRequest(BaseModel):
    instruction: str


@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    message = generate_ai_text(request.instruction)
    return {"status": "sent", "message": message, "clarification": ""}
