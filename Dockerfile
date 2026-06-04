FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Install Xvfb for virtual display (Playwright headless=False requires a display)
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

# Sessions directory is mounted as a volume at runtime — create the mount point
RUN mkdir -p backend/sessions/facebook

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PORT=8080
ENV DISPLAY=:99
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
