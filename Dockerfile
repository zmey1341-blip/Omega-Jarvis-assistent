FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей для корректной работы Chromium в режиме headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY requirements.txt .

# Принудительно сбрасываем кэш pip и ставим пакеты
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Установка браузера Playwright и системных библиотек Linux (.so файлов)
RUN playwright install chromium \
    && playwright install-deps chromium

# Копируем проект (содержимое папки jarvis-omega переносится в корень /app)
COPY jarvis-omega/ .

# Добавляем корень в PYTHONPATH, чтобы Python видел модули при любых раскладах импорта
ENV PYTHONPATH=/app

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
