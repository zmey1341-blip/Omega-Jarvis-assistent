FROM python:3.10-slim

WORKDIR /app

# Устанавливаем системные утилиты для работы с сетью и библиотеками Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей (убедись, что в нем прописан playwright)
COPY requirements.txt .

# Устанавливаем все библиотеки Python из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем бинарники Chromium и все системные библиотеки (.so зависимости для работы в headless-режиме)
RUN playwright install chromium
RUN playwright install-deps chromium

# Копируем исходный код проекта
COPY jarvis-omega/ .

# Указываем порт по умолчанию для Render
EXPOSE 10000

# Команда для запуска веб-сервера. Если у тебя стартовый файл называется по-другому, поменяй main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
