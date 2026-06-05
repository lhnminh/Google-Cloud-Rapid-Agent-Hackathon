#!/bin/bash
set -e

# Start virtual display
Xvfb :99 -screen 0 1280x900x24 -nolisten tcp &
export DISPLAY=:99
sleep 2

# Share the virtual display over VNC (no password, local only)
x11vnc -display :99 -nopw -forever -quiet &

# Serve the VNC display in the browser via noVNC on port 6080
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}"
