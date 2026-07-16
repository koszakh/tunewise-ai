FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей (нужны для сборки некоторых библиотек)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# По умолчанию запускаем FastAPI, но этот же образ мы переиспользуем для Celery
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
