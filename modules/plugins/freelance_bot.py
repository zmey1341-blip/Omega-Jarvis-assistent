import logging
import httpx
import xml.etree.ElementTree as ET

logger = logging.getLogger("jarvis.plugins.freelance")

class FreelanceAutomator:
    def __init__(self, router, api_key_биржи: str = ""):
        self._router = router
        self._api_key = api_key_биржи

    async def hunt_and_solve(self) -> tuple[str, float]:
        # 1. Парсим открытую RSS-ленту заказов Хабр Фриланса (для теста)
        rss_url = "https://freelance.habr.com/tasks.rss"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(rss_url)
            if resp.status_code != 200:
                return "Не удалось получить список задач с биржи", 0.0

        # Parse XML
        root = ET.fromstring(resp.content)
        tasks = root.findall(".//item")
        
        if not tasks:
            return "Новых задач на бирже пока нет.", 0.0

        # Берем самую свежую задачу
        latest_task = tasks[0]
        title = latest_task.find("title").text
        description = latest_task.find("description").text
        link = latest_task.find("link").text

        # 2. Фильтруем задачи: Jarvis берется только за то, в чем он силен (тексты, код, скрипты)
        keywords = ["написать", "текст", "python", "копирайт", "статья", "telegram"]
        if not any(kw in title.lower() or kw in description.lower() for kw in keywords):
            return f"Пропущена задача '{title}' (не подходит по тематике)", 0.0

        # 3. Jarvis генерирует идеальное ТЗ или тестовое решение для отклика
        prompt = (
            f"Действуй как опытный фрилансер. Сгенерируй профессиональный, вежливый отклик на заказ.\n"
            f"Название заказа: {title}\n"
            f"Описание: {description}\n\n"
            f"Напиши, почему мы идеально подходим, и предложи базовый план реализации."
        )
        
        messages = [{"role": "user", "content": prompt}]
        proposal = await self._router.complete(messages)

        # 4. В реальности здесь идет POST-запрос к API биржи для отправки отклика.
        # Пока симулируем отправку:
        logger.info(f"[Freelance] Отправлен отклик на задачу: {link}")
        
        # Симулируем потенциальный доход (например, средняя цена копеечного заказа)
        potential_revenue = 5.0 # $5 за простой текст/скрипт в случае успеха
        
        return f"Отправлен отклик на заказ '{title}'. Сгенерирован ответ: {proposal[:60]}...", potential_revenue