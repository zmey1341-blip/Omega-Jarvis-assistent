import os
import asyncio
import logging
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger("jarvis.plugins.advego_jobs")

class AdvegoJobHunter:
    def __init__(self, router=None):
        self._router = router
        self.cookie_sid = os.getenv("ADVEGO_COOKIE_SID", "")
        self.cookie_token = os.getenv("ADVEGO_COOKIE_TOKEN", "")
        
        # Настройки прокси (добавь эти переменные в Render, если используешь прокси)
        # Формат: http://username:password@proxy_address:port
        self.proxy_url = os.getenv("PROXY_URL", "") 
        
        self.screenshot_dir = Path("/app/outputs") if os.path.exists("/app") else Path("./outputs")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Путь для сохранения снапшота заказов
        self.snapshot_path = self.screenshot_dir / "snapshot.json"

    async def hunt_and_execute(self) -> tuple[str, float]:
        logger.info("[Advego] Автономный поиск пути пробива... Запуск Playwright.")
        
        if not self.cookie_sid or not self.cookie_token:
            return "Ошибка: Не заданы куки авторизации.", 0.0

        async with async_playwright() as p:
            kiwi_user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
            
            # Если переменная PROXY_URL пустая, запускаемся без прокси, если заполнена — заворачиваем трафик
            launch_options = {
                "headless": True,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars"
                ]
            }
            
            if self.proxy_url:
                logger.info("[Advego] Подключение через прокси сервер...")
                # Playwright умеет парсить строку прокси или принимать объектом
                launch_options["proxy"] = {"server": self.proxy_url}

            browser = await p.chromium.launch(**launch_options)
            
            context = await browser.new_context(
                user_agent=kiwi_user_agent,
                viewport={"width": 390, "height": 844},
                device_scale_factor=3,
                is_mobile=True,
                has_touch=True,
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                extra_http_headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Sec-Ch-Ua-Mobile": "?1",
                    "Sec-Ch-Ua-Platform": '"Android"'
                }
            )
            
            # Накатываем куки
            await context.add_cookies([
                {"name": "domain_sid", "value": self.cookie_sid, "domain": ".advego.com", "path": "/"},
                {"name": "token", "value": self.cookie_token, "domain": ".advego.com", "path": "/"}
            ])
            
            page = await context.new_page()
            
            # Глубокий патч runtime-характеристик браузера против Cloudflare/Advego Antivirus
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ? 
                    Promise.resolve({ state: Notification.permission }) : 
                    originalQuery(parameters)
                );
            """)

            try:
                # Пробуем пробиться напрямую в обход главной страницы
                logger.info("[Advego] Попытка прорыва в ленту заказов...")
                await page.goto("https://advego.com/job/find/", wait_until="domcontentloaded", timeout=30000)
                
                await asyncio.sleep(random.uniform(3.0, 5.0))
                current_url = page.url
                
                if "login" in current_url:
                    logger.warning("[Advego] Пробив не удался: Сервер Advego сбросил сессию на страницу авторизации.")
                    await browser.close()
                    return "Сессия отклонена сервером (требуется прокси под регион Kiwi или новые куки).", 0.0

                # Проверка на Cloudflare
                title = await page.title()
                if "Cloudflare" in title or "Just a moment" in title:
                    logger.warning("[Advego] Путь заблокирован Cloudflare.")
                    await browser.close()
                    return "Блокировка Cloudflare.", 0.0

                logger.info("[Advego] Ура! Прорыв успешен. Начинаю сбор 20 заказов...")
                
                # Делаем скриншот верстки мобилки для анализа, если селекторы не сработают
                debug_screen = self.screenshot_dir / "advego_mobile_screen.png"
                await page.screenshot(path=str(debug_screen), full_page=True)
                logger.info(f"[Advego] Снимок экрана сохранен для отладки: {debug_screen}")

                # --- БЛОК СБОРА ДАННЫХ (БЕЗОПАСНЫЙ) ---
                parsed_jobs = []
                try:
                    # Пробуем дождаться хотя бы какого-нибудь стандартного контейнера
                    await page.wait_for_selector(".job_task, [id^='task_'], .job-item, .task-item", timeout=5000)
                    job_elements = await page.query_selector_all(".job_task, [id^='task_'], .job-item, .task-item")
                except Exception:
                    logger.warning("[Advego] Мобильные селекторы не найдены, переключаюсь на сбор по ссылкам и тегам.")
                    # Запасной вариант: забираем все ссылки, ведущие на карточки задач
                    job_elements = await page.query_selector_all("a[href*='/job/'], .task")

                if not job_elements:
                    logger.error("[Advego] Не удалось зацепиться ни за один элемент заказа на странице.")
                else:
                    for element in job_elements[:20]:
                        try:
                            job_id = await element.get_attribute("id") or "unknown"
                            
                            # Вытягиваем весь текст, что есть в блоке
                            raw_text = await element.inner_text()
                            if raw_text:
                                # Форматируем строку: убираем лишние переносы и берем первые 6 слов для заголовка
                                clean_text = " ".join(raw_text.split())
                                job_title = " ".join(clean_text.split()[:6]) + "..."
                            else:
                                job_title = "Без названия"
                            
                            parsed_jobs.append({
                                "id": job_id.replace("task_", ""),
                                "title": job_title.strip(),
                                "price": "См. скриншот/верстку"
                            })
                        except Exception:
                            continue
                
                # Сохраняем результат в файл snapshot.json
                self.snapshot_path.write_text(json.dumps(parsed_jobs, ensure_ascii=False, indent=2))
                logger.info(f"[Advego] Сбор завершен. Успешно сохранено {len(parsed_jobs)} элементов в snapshot.json.")
                
                await browser.close()
                return f"Успешный прорыв! Собрано элементов: {len(parsed_jobs)}", 0.0

            except Exception as e:
                logger.error(f"[Advego] Ошибка при попытке прорыва/парсинга: {e}")
                await browser.close()
                return f"Сбой метода: {e}", 0.0
