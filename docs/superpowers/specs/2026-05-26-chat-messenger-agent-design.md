# Design Spec: Chat-to-Messenger Agent (Prototype v0)

**Date:** 2026-05-26
**Status:** Approved

---

## Overview

A chat interface where the user types a natural-language instruction and an AI agent browser-navigates Facebook Messenger to send the message on their behalf.

**First prototype scope:** Facebook Messenger only.

---

## User Flow

1. User opens the Streamlit chat UI
2. User types an instruction, e.g. _"Send John a reminder about tomorrow's meeting at 10am"_
3. UI shows a loading indicator ("Sending via Messenger…")
4. Backend agent navigates a real browser to Messenger, finds the recipient, drafts, and sends the message
5. UI displays the result:
   - **Success:** confirms who was messaged and what was sent
   - **Clarification needed:** asks the user to disambiguate (e.g. "Found 2 contacts named John — which one?")
   - **Failed:** reports what went wrong

### Disambiguation loop

If the agent cannot resolve the recipient (name not found, or multiple matches), it returns `clarification_needed` and the chat prompts the user. The user replies with more detail, and the agent retries.

---

## Architecture

```
Streamlit UI  →  POST /send-message  →  FastAPI backend  →  browser-use + Claude API  →  Messenger (browser)
```

### Components

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| Chat UI | Streamlit | Render chat, POST instruction, display result |
| Backend API | FastAPI | Receive request, orchestrate agent, return result |
| Browser Agent | browser-use + Claude API | Parse instruction, navigate Messenger, send message |

### API Contract

**Endpoint:** `POST /send-message`

Request:
```json
{ "instruction": "Send John a reminder about tomorrow's meeting" }
```

Response:
```json
{
  "status": "sent" | "clarification_needed" | "failed",
  "message": "Sent to John Smith: 'Hey John, just a reminder about your meeting tomorrow at 10am!'",
  "clarification": "Found 2 contacts named John. Which one did you mean?"
}
```

---

## Out of Scope (Prototype v0)

- Live browser view embedded in the chat (backlog)
- Other channels (SMS, WhatsApp, LinkedIn, Telegram)
- AI content optimization (time-of-day, engagement patterns)
- User authentication
- Message history / audit log

---

## Backlog

- **Live agent view:** embed a live browser window inside the chat so the user can watch the agent navigate Messenger in real time
- **Multi-channel:** extend to SMS, WhatsApp, Telegram, LinkedIn
- **AI optimization:** optimize message timing and tone based on engagement patterns

---

## Tech Stack

- **Python** throughout (frontend + backend in the same language)
- **Streamlit** — chat UI
- **FastAPI** — single-endpoint backend
- **browser-use** — browser automation library for the agent
- **Claude API** — LLM powering the agent's reasoning
