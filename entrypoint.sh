#!/bin/bash
set -e

XVFB_LOG=/tmp/xvfb.log
X11VNC_LOG=/tmp/x11vnc.log
WEBSOCKIFY_LOG=/tmp/websockify.log

# Start virtual display
export DISPLAY=:99
Xvfb "$DISPLAY" -screen 0 1280x900x24 -nolisten tcp >"$XVFB_LOG" 2>&1 &
XVFB_PID=$!

for _ in $(seq 1 20); do
  if [ -S /tmp/.X11-unix/X99 ] && kill -0 "$XVFB_PID" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if ! kill -0 "$XVFB_PID" 2>/dev/null; then
  echo "Xvfb failed to start. Log:"
  cat "$XVFB_LOG"
  exit 1
fi

# Share the virtual display over VNC (no password, local only)
x11vnc -display "$DISPLAY" -nopw -forever -shared -listen 0.0.0.0 -rfbport 5900 -quiet >"$X11VNC_LOG" 2>&1 &
X11VNC_PID=$!

sleep 1
if ! kill -0 "$X11VNC_PID" 2>/dev/null; then
  echo "x11vnc failed to start. Log:"
  cat "$X11VNC_LOG"
  exit 1
fi

# Serve the VNC display in the browser via noVNC on port 6080
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >"$WEBSOCKIFY_LOG" 2>&1 &
WEBSOCKIFY_PID=$!

sleep 1
if ! kill -0 "$WEBSOCKIFY_PID" 2>/dev/null; then
  echo "websockify failed to start. Log:"
  cat "$WEBSOCKIFY_LOG"
  exit 1
fi

echo "Virtual display ready on $DISPLAY; noVNC available on port 6080."

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}"
