FROM python:3.10-slim

WORKDIR /app

# Устанавливаем библиотеки напрямую
RUN pip install --no-cache-dir fastapi uvicorn aiogram python-dotenv httpx

# Копируем всё содержимое папки jarvis-omega прямо в рабочую директорию /app
COPY jarvis-omega/ .

# Теперь main.py окажется точно там, где нужно, и запустится без ошибок
CMD ["python", "main.py"]

