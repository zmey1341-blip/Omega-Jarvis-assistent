FROM python:3.10-slim

WORKDIR /app

# Обновляем систему и ставим системные библиотеки для Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Копируем списки зависимостей
COPY requirements.txt .

# Ставим свежие пакеты
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Устанавливаем сам Playwright браузер и его бинарные зависимости
RUN playwright install chromium \
    && playwright install-deps chromium

# Копируем остальной проект
COPY jarvis-omega/ .

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
