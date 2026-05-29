# Build Plan
_Last updated: 2026-05-29_

## What We're Building

A multi-step AI agent that:
1. Takes a natural-language instruction from the user ("Send John a reminder about tomorrow's meeting")
2. Uses Fivetran MCP to look up contact data
3. Uses Gemini to draft the message
4. Sends the message via Facebook Messenger using a browser agent

---

## Current State

| Component | Status |
|---|---|
| Streamlit UI | Replaced with HTML/JS frontend |
| FastAPI backend | Running, serves frontend at `http://localhost:8000` |
| Gemini text generation | Working (`backend/text_function.py`) |
| Browser automation (Playwright) | Code exists in `test/` but not wired to backend |
| Google Cloud Agent Builder | Not set up |
| Fivetran MCP | Not set up |
| Scheduling | Not started |

---

## Phase 1: Browser Agent (Send the Message)

The goal is to wire up the backend so that after Gemini drafts the message, Playwright actually sends it via Facebook Messenger.

### Step 1.1 — Move Playwright code into the backend

- The Playwright scripts currently live in `test/browser/`. They need to be moved into `backend/` so the FastAPI server can call them.
- Create `backend/browser.py` containing:
  - `launch_browser()` — launches a persistent Chromium session using a saved Facebook login
  - `send_messenger(recipient, message)` — navigates to Messenger, finds the contact, sends the message

### Step 1.2 — Save a Facebook session

Before the browser agent can send messages, it needs to be logged into Facebook. This is done once manually:

1. Run a script that opens a browser window
2. Log into Facebook manually
3. Close the browser — Playwright saves the session to `./sessions/facebook/`
4. From now on, the browser agent reuses this saved session (no login needed)

**Important:** Add `sessions/` to `.gitignore` — never commit login sessions.

### Step 1.3 — Parse the instruction

Right now the backend passes the raw user instruction directly to Gemini. We need to extract two things from the instruction:
- **Recipient name** — e.g., "John"
- **Message intent** — e.g., "remind him about tomorrow's meeting"

Options:
- Ask Gemini to return structured JSON: `{ "recipient": "John", "message": "..." }`
- Or use a simple prompt that instructs Gemini to return `RECIPIENT: ... \n MESSAGE: ...`

### Step 1.4 — Wire it all together in `backend/main.py`

The `/send-message` endpoint should:
1. Call Gemini with the instruction → get back recipient + drafted message
2. Call `send_messenger(recipient, message)` from `backend/browser.py`
3. Return `{ "status": "sent", "message": <drafted message> }` to the frontend

---

## Phase 2: Google Cloud Agent Builder

Google Cloud Agent Builder replaces the current direct Gemini call. Instead of calling Gemini directly from `text_function.py`, the agent handles the entire orchestration.

### Step 2.1 — Create a Google Cloud project agent

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Agent Builder** (search for it in the top bar)
3. Click **Create Agent**
4. Choose **Conversational Agent** (not Search)
5. Give it a name (e.g., `forgettext-agent`)
6. Select your Google Cloud project

### Step 2.2 — Define the agent's tools

In Agent Builder, you define what tools the agent can use. For our project:
- **Tool 1:** Send a message (calls our FastAPI backend)
- **Tool 2:** Look up a contact (calls Fivetran MCP — see Phase 3)

### Step 2.3 — Connect your backend to the agent

Agent Builder can call external APIs via **webhooks**. You'll set up a webhook that points to your FastAPI `/send-message` endpoint.

For local development, you'll need to expose your local server to the internet using a tool like **ngrok**:

```bash
ngrok http 8000
```

This gives you a public URL (e.g., `https://abc123.ngrok.io`) that Agent Builder can call.

### Step 2.4 — Update the frontend to talk to Agent Builder

Instead of calling `http://localhost:8000/send-message` directly, the frontend will send the instruction to the Google Cloud Agent endpoint. The agent then decides what to do.

---

## Phase 3: Fivetran MCP Integration

Fivetran MCP gives the agent access to Fivetran's data connectors as a tool. In our case, this means the agent can query a contacts database to resolve recipient names.

### Step 3.1 — Set up a Fivetran account

1. Sign up at [fivetran.com](https://fivetran.com) (free trial available)
2. Create a new **destination** — this is where synced data lands (e.g., a Google BigQuery or PostgreSQL database)
3. Create a **connector** — this is the data source (e.g., a Google Sheets contact list, or a CRM)

For a hackathon, the simplest setup is:
- **Source:** Google Sheets (a simple contact list with Name + Messenger username)
- **Destination:** BigQuery (Google Cloud's data warehouse — integrates well with Agent Builder)

### Step 3.2 — Set up the Fivetran MCP server

Fivetran provides an MCP server that lets AI agents query your synced data.

1. Get your Fivetran API key from the Fivetran dashboard
2. Add to `.env`:
   ```
   FIVETRAN_API_KEY=your_key_here
   FIVETRAN_API_SECRET=your_secret_here
   ```
3. Add `FIVETRAN_API_KEY` and `FIVETRAN_API_SECRET` to `.env.example` (without values)
4. Configure the Fivetran MCP server — documentation at [Fivetran MCP docs](https://fivetran.com/docs/mcp)

### Step 3.3 — Give the agent access to Fivetran MCP

In Google Cloud Agent Builder, register the Fivetran MCP server as a tool. The agent can then call it to look up contacts by name before drafting a message.

---

## Phase 4: Scheduling

Allow users to say "Send John a message tomorrow at 9am" and have it actually send at that time.

### Step 4.1 — Store scheduled messages

Add a simple database (SQLite for local dev, Cloud SQL for production) with a table:

```
scheduled_messages
- id
- recipient
- message
- send_at (datetime)
- status (pending / sent / failed)
```

### Step 4.2 — Add a scheduler

Use **Google Cloud Scheduler** to trigger a check every minute:
1. Set up a Cloud Scheduler job that calls your backend at `POST /process-scheduled`
2. That endpoint checks the database for any messages where `send_at <= now` and `status = pending`
3. For each one, calls the browser agent to send it

### Step 4.3 — Update the frontend

Add a way for the user to specify a send time — either:
- Natural language ("tomorrow at 9am") parsed by Gemini
- Or a simple datetime picker in the UI

---

## Recommended Build Order

1. **Phase 1** — Get the browser agent working end-to-end first. This is the core demo.
2. **Phase 3** — Set up Fivetran MCP (required by hackathon rules).
3. **Phase 2** — Integrate Google Cloud Agent Builder to orchestrate the flow.
4. **Phase 4** — Add scheduling last, only if time allows.

---

## Open Questions

- What data source will Fivetran sync? (Google Sheets contact list is the simplest option)
- Will the demo use a real Facebook account or a test account?
- Who owns the Google Cloud project — and does your partner have access?
