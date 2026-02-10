FROM python:3.12-slim

WORKDIR /app

# Системні пакети для psutil та pygame
RUN apt-get update && apt-get install -y \
    gcc \
    libsdl2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Додаємо google-generativeai прямо сюди, щоб ігнорувати кеш requirements.txt
RUN pip install --no-cache-dir google-generativeai -r requirements.txt

COPY . .

# Тимчасовий запуск за замовчуванням
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
