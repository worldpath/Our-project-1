# Dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . /app

# Defaults (overridden by .env / compose)
ENV CONFIG_PATH=config/aggressive_production.yaml \
    DASHBOARD_HOST=0.0.0.0 \
    DASHBOARD_PORT=8000

EXPOSE 8000

# We start the bot from compose with an absolute path, but leave a sane default here too:
CMD ["bash","-lc","python /app/main.py"]
