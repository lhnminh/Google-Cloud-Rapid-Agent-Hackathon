# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Universal Message Automation Engine** — a centralized platform for scheduling and automating message delivery across disparate communication channels (WhatsApp, Telegram, SMS, LinkedIn, etc.).

This project is in **early ideation/design phase**. No production code exists yet; `back-end/` and `front-end/` contain only empty placeholder files.

## Planned Architecture

| Layer | Technology | Role |
| :--- | :--- | :--- |
| Data Integration | Fivetran (ETL) | Sync message status across services |
| Orchestration | Google Cloud Agent Builder | Scheduling rules, failure logic, multi-step workflows |
| Backend | Python or Node.js (TBD) | API communication, auth, business logic |
| Database | Cloud SQL or MongoDB (TBD) | Scheduled messages, metadata, sending history |

**Phased rollout:**
- Phase 0 (current): Define core API endpoints and data flow
- Phase I: Scheduling for 1-2 primary services (WhatsApp, SMS) + basic logging
- Phase II: AI content optimization + secondary channels (LinkedIn)

## Stack Decisions Not Yet Made

- Backend language: Python vs Node.js
- Database: Cloud SQL (relational) vs MongoDB (document)
- Frontend: not yet defined

When starting implementation, confirm these choices before writing code.

---

## Development Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
