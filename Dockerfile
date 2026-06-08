FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data && chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app/src:/app
ENV PYTHONIOENCODING=utf-8

EXPOSE 8001

ENTRYPOINT ["/app/entrypoint.sh"]
