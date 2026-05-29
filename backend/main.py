from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class SendMessageRequest(BaseModel):
    instruction: str


@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    print(f"Received: {request.instruction}")
    return {"status": "sent", "message": request.instruction, "clarification": ""}
