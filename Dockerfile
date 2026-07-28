FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN python -m pip install --upgrade pip && pip install -r requirements.txt
COPY . .
RUN mkdir -p /app/data /app/models /app/logs

EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
