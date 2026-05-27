FROM python:3.10-slim

WORKDIR /app

# Жестко прописываем переменные окружения прямо в систему
ENV TELEGRAM_BOT_TOKEN="8909414413:AAFa6PLvuP0ZLz7yxZJMJ-d2q601ndFonmk"
ENV TELEGRAM_ADMIN_ID="422343797"

# Подсовываем реальный ключ OpenRouter (зарегистрируй его, это бесплатно)
ENV OPENROUTER_API_KEY="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
# На всякий случай дублируем его в Zhipu, если до OpenRouter код долго идет
ENV ZHIPU_API_KEY="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"

RUN pip install --no-cache-dir fastapi uvicorn aiogram python-dotenv httpx

COPY jarvis-omega/ .

CMD ["python", "main.py"]
