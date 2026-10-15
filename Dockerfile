# Small official Python image
FROM python:3.12-slim

# No .pyc files, logs appear immediately; Render tells the app which port to use
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

# Install dependencies first, so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy only the code the app needs
COPY app.py modes.py ./
COPY templates ./templates

# Security: never run the app as root inside the container
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 10000

# Docker can check the app's pulse too
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ['PORT'])" || exit 1

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 app:app"]
