# Chat-to-Messenger Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit chat UI that takes natural-language instructions and sends Facebook Messenger messages via a browser-use agent.

**Architecture:** Streamlit frontend POSTs user instructions to a FastAPI backend (`POST /send-message`). The backend runs a browser-use + Claude agent that navigates Messenger in a real browser to find the recipient and send the message. The API returns one of three statuses: `sent`, `clarification_needed`, or `failed`.

**Tech Stack:** Python 3.11+, Streamlit, FastAPI, uvicorn, browser-use, langchain-anthropic, httpx, python-dotenv, pytest, pytest-asyncio

---

## File Map

| File | Responsibility |
| :--- | :--- |
| `requirements.txt` | All Python dependencies |
| `.env.example` | Template for required environment variables |
| `backend/__init__.py` | Makes `backend` importable as a Python package |
| `backend/main.py` | FastAPI app — single `POST /send-message` endpoint |
| `backend/agent.py` | `run_agent(instruction)` — browser-use agent + output parser |
| `frontend/app.py` | Streamlit chat UI |
| `tests/test_api.py` | pytest tests for the endpoint and output parser |

> **Note:** The existing `back-end/` and `front-end/` directories use hyphens which are invalid in Python module names. Task 1 renames them to `backend/` and `frontend/`.

---

### Task 1: Rename directories and set up dependencies

**Files:**
- Rename: `back-end/` → `backend/`
- Rename: `front-end/` → `frontend/`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `backend/__init__.py`

- [ ] **Step 1: Rename the directories**

```bash
cd c:/Users/VHV/Documents/Learn/Google-Cloud-Rapid-Agent-Hackathon
mv back-end backend
mv front-end frontend
```

- [ ] **Step 2: Create requirements.txt**

```
streamlit>=1.35.0
fastapi>=0.111.0
uvicorn>=0.30.0
browser-use>=0.1.40
langchain-anthropic>=0.1.21
httpx>=0.27.0
python-dotenv>=1.0.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Create .env.example**

```
ANTHROPIC_API_KEY=your_key_here
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 5: Copy .env.example and fill in your Anthropic API key**

```bash
cp .env.example .env
# Open .env and paste your key from https://console.anthropic.com
```

- [ ] **Step 6: Create backend/__init__.py** (empty file — makes `backend` importable)

```bash
touch backend/__init__.py
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example backend/__init__.py
git commit -m "feat: set up project dependencies and rename directories"
```

---

### Task 2: FastAPI endpoint (test-first)

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_api.py`
- Create: `backend/main.py`

- [ ] **Step 1: Create tests/__init__.py** (empty)

```bash
touch tests/__init__.py
```

- [ ] **Step 2: Write the failing tests in tests/test_api.py**

```python
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def _client():
    from backend.main import app
    return TestClient(app)


def test_send_message_returns_sent():
    with patch("backend.main.run_agent", new=AsyncMock(return_value={
        "status": "sent",
        "message": "John Smith: Hey John, reminder about tomorrow!",
        "clarification": ""
    })):
        response = _client().post("/send-message", json={"instruction": "Send John a reminder"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert data["message"] != ""
    assert data["clarification"] == ""


def test_send_message_returns_clarification_needed():
    with patch("backend.main.run_agent", new=AsyncMock(return_value={
        "status": "clarification_needed",
        "message": "",
        "clarification": "Found 2 contacts named John. Which one?"
    })):
        response = _client().post("/send-message", json={"instruction": "Send John a message"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["clarification"] != ""


def test_send_message_returns_failed():
    with patch("backend.main.run_agent", new=AsyncMock(return_value={
        "status": "failed",
        "message": "Could not log into Messenger",
        "clarification": ""
    })):
        response = _client().post("/send-message", json={"instruction": "Send John a message"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["message"] != ""
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
cd c:/Users/VHV/Documents/Learn/Google-Cloud-Rapid-Agent-Hackathon
pytest tests/test_api.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.main'`

- [ ] **Step 4: Create a stub backend/agent.py** (so imports resolve)

```python
async def run_agent(instruction: str) -> dict:
    return {"status": "sent", "message": "stub", "clarification": ""}
```

- [ ] **Step 5: Create backend/main.py**

```python
from fastapi import FastAPI
from pydantic import BaseModel
from backend.agent import run_agent

app = FastAPI()


class SendMessageRequest(BaseModel):
    instruction: str


class SendMessageResponse(BaseModel):
    status: str
    message: str
    clarification: str


@app.post("/send-message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    result = await run_agent(request.instruction)
    return SendMessageResponse(**result)
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/test_api.py -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/agent.py tests/__init__.py tests/test_api.py
git commit -m "feat: add FastAPI endpoint with passing tests"
```

---

### Task 3: Browser-use agent

**Files:**
- Modify: `backend/agent.py`
- Modify: `tests/test_api.py` (add parser unit tests)

- [ ] **Step 1: Add parser unit tests to tests/test_api.py**

Append to the end of `tests/test_api.py`:

```python
def test_parse_sent():
    from backend.agent import _parse_agent_output
    result = _parse_agent_output("SENT: John Smith: Hey John, reminder about tomorrow!")
    assert result == {
        "status": "sent",
        "message": "John Smith: Hey John, reminder about tomorrow!",
        "clarification": ""
    }


def test_parse_clarification():
    from backend.agent import _parse_agent_output
    result = _parse_agent_output("CLARIFICATION_NEEDED: Found 2 contacts named John. Which one?")
    assert result == {
        "status": "clarification_needed",
        "message": "",
        "clarification": "Found 2 contacts named John. Which one?"
    }


def test_parse_failed():
    from backend.agent import _parse_agent_output
    result = _parse_agent_output("FAILED: Could not find recipient")
    assert result == {
        "status": "failed",
        "message": "Could not find recipient",
        "clarification": ""
    }


def test_parse_unexpected_output():
    from backend.agent import _parse_agent_output
    result = _parse_agent_output("something random")
    assert result["status"] == "failed"
    assert "something random" in result["message"]
```

- [ ] **Step 2: Run tests — verify parser tests fail**

```bash
pytest tests/test_api.py -v -k "parse"
```

Expected: `AttributeError: module 'backend.agent' has no attribute '_parse_agent_output'`

- [ ] **Step 3: Replace backend/agent.py with the real implementation**

```python
import os
from dotenv import load_dotenv
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

load_dotenv()

_PROMPT_TEMPLATE = """
You are a messaging agent. The user wants you to: {instruction}

Go to https://www.facebook.com/messages in the browser.
Find the recipient mentioned in the instruction and send them the message described.

When you are completely done, output EXACTLY one of these lines as your final response:
- If you sent the message successfully: SENT: <recipient full name>: <exact message you sent>
- If multiple contacts match the name and you cannot determine which one: CLARIFICATION_NEEDED: <question to ask the user>
- If you could not complete the task for any reason: FAILED: <reason>
"""


async def run_agent(instruction: str) -> dict:
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    task = _PROMPT_TEMPLATE.format(instruction=instruction)
    agent = Agent(task=task, llm=llm)
    result = await agent.run()
    output = result.final_result() or ""
    return _parse_agent_output(output)


def _parse_agent_output(output: str) -> dict:
    output = output.strip()
    if output.startswith("SENT:"):
        return {"status": "sent", "message": output[len("SENT:"):].strip(), "clarification": ""}
    if output.startswith("CLARIFICATION_NEEDED:"):
        return {"status": "clarification_needed", "message": "", "clarification": output[len("CLARIFICATION_NEEDED:"):].strip()}
    if output.startswith("FAILED:"):
        return {"status": "failed", "message": output[len("FAILED:"):].strip(), "clarification": ""}
    return {"status": "failed", "message": f"Unexpected agent output: {output}", "clarification": ""}
```

- [ ] **Step 4: Run all tests — verify they pass**

```bash
pytest tests/test_api.py -v
```

Expected: `7 passed` (3 API tests + 4 parser tests)

- [ ] **Step 5: Commit**

```bash
git add backend/agent.py tests/test_api.py
git commit -m "feat: implement browser-use agent and output parser"
```

---

### Task 4: Streamlit chat UI

**Files:**
- Modify: `frontend/app.py`

- [ ] **Step 1: Replace frontend/app.py with the chat UI**

```python
import httpx
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.title("Message Agent")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Who should I message and what should I say?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

instruction = st.chat_input("Tell me who to message and what to say…")

if instruction:
    st.session_state.messages.append({"role": "user", "content": instruction})
    with st.chat_message("user"):
        st.write(instruction)

    with st.chat_message("assistant"):
        with st.spinner("Sending via Messenger…"):
            try:
                response = httpx.post(
                    f"{BACKEND_URL}/send-message",
                    json={"instruction": instruction},
                    timeout=120.0,
                )
                data = response.json()
            except Exception as e:
                data = {"status": "failed", "message": str(e), "clarification": ""}

        if data["status"] == "sent":
            reply = f"Done! {data['message']}"
        elif data["status"] == "clarification_needed":
            reply = data["clarification"]
        else:
            reply = f"Something went wrong: {data['message']}"

        st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
```

- [ ] **Step 2: Start the backend** (keep this terminal open)

```bash
cd c:/Users/VHV/Documents/Learn/Google-Cloud-Rapid-Agent-Hackathon
uvicorn backend.main:app --reload --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 3: Start the Streamlit app** (open a second terminal)

```bash
cd c:/Users/VHV/Documents/Learn/Google-Cloud-Rapid-Agent-Hackathon
streamlit run frontend/app.py
```

Expected: browser opens at `http://localhost:8501` showing the chat UI with the welcome message.

- [ ] **Step 4: Manual smoke test**

In the chat UI, type: `Send yourself a test message saying hello`

Expected:
- Spinner shows "Sending via Messenger…"
- A real browser window opens and navigates to facebook.com/messages
- Agent finds the recipient and sends the message
- Chat shows: `Done! <recipient name>: <message sent>`

- [ ] **Step 5: Commit**

```bash
git add frontend/app.py
git commit -m "feat: add Streamlit chat UI"
```

---

## Running the App

**Backend** (Terminal 1):
```bash
uvicorn backend.main:app --reload --port 8000
```

**Frontend** (Terminal 2):
```bash
streamlit run frontend/app.py
```

**Tests:**
```bash
pytest tests/ -v
```
