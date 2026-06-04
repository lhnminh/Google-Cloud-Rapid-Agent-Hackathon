#!/bin/bash
set -e

# Start a virtual display so Playwright can run headless=False (needed for Facebook login)
Xvfb :99 -screen 0 1280x900x24 -nolisten tcp &
export DISPLAY=:99

# Give Xvfb a moment to initialize
sleep 1

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}"
