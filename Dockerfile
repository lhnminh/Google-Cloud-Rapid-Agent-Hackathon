FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Install Xvfb for virtual display, x11vnc to share it, novnc to access it from a browser
RUN apt-get update && apt-get install -y xvfb x11vnc novnc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium

COPY backend/ backend/
COPY frontend/ frontend/

# Sessions directory is mounted as a volume at runtime — create the mount point
RUN mkdir -p backend/sessions/facebook

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PORT=8080
ENV DISPLAY=:99
ENV IS_DOCKER=true
EXPOSE 8080
EXPOSE 6080

ENTRYPOINT ["/entrypoint.sh"]
