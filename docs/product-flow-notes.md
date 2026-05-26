# Product Flow Notes
_Working notes — updated as design is refined_

## What We're Building

A **chat interface** where a user types a natural-language instruction and an AI agent writes and sends a message on their behalf.

**First prototype target:** Facebook Messenger

---

## Core Flow (v0)

1. User opens the chat interface
2. User types a natural-language instruction
   - e.g., _"Send John a reminder about tomorrow's meeting"_
3. AI agent identifies the recipient ("John") from a contact list
4. AI drafts the message
5. Message is sent via Messenger

---

## Open Questions (still deciding)

- Does the user see a preview before the message sends, or is it fully automatic?
- How does the AI resolve recipient names — Messenger contacts, a CRM, or a separate contact book?
- What does the AI do if it can't find the recipient or is unsure?

---

_Last updated: 2026-05-26_
