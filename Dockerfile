FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

# Migraciones + bootstrap idempotente + uvicorn (ver scripts/entrypoint.sh)
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
