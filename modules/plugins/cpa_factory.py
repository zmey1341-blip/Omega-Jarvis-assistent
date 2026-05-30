import logging
import httpx

logger = logging.getLogger("jarvis.plugins.cpa")

class CPAContentFactory:
    def __init__(self, router, telegram_bot_token: str, channel_id: str):
        self._router = router
        self._bot_token = telegram_bot_token
        self._channel_id = channel_id

    async def generate_and_post(self) -> str:
        # 1. Выбираем трендовый оффер (в реале тут будет парсинг твоих реф-ссылок/офферов)
        product_title = "Беспроводные наушники с активным шумоподавлением"
        ref_link = "https://ozon.ru/referral_link_placeholder" # Твоя рефка
        
        # 2. Просим ИИ написать крутой продающий пост
        prompt = (
            f"Напиши короткий, нативный и цепляющий пост для Telegram-канала с обзором на: '{product_title}'. "
            f"Используй эмодзи, выдели боли пользователя (шум в метро, плохой звук) и сделай призыв к действию. "
            f"В конце поста обязательно вставь ссылку: {ref_link}"
        )
        
        messages = [{"role": "user", "content": prompt}]
        post_content = await self._router.complete(messages)
        
        # 3. Публикуем в Telegram-канал через Bot API
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = {
            "chat_id": self._channel_id,
            "text": post_content,
            "parse_mode": "HTML"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Telegram API Error: {resp.text}")
                
        return f"Успешно опубликован пост про '{product_title}' в канал {self._channel_id}"