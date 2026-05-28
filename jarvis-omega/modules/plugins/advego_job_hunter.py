import asyncio
import random
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger("jarvis.plugins.advego_jobs")

class AdvegoJobHunter:
    def __init__(self, router):
        self._router = router
        self._login = "zmey1341@mail.ru"
        self._password = "Samsung777+"

    async def hunt_and_execute(self):
        async with async_playwright() as p:
            # Запускаем браузер с аргументами, которые сложнее заблокировать
            browser = await p.chromium.launch(headless=True, args=[
                "--no-sandbox", 
                "--disable-blink-features=AutomationControlled",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ])
            context = await browser.new_context()
            page = await context.new_page()

            # Скрываем признаки робота
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                # 1. Переход на страницу логина
                await page.goto("https://advego.com/login/")
                await asyncio.sleep(random.uniform(3, 5))

                # 2. Логин (проверяем, есть ли форма)
                login_input = await page.query_selector('input[name="login"]')
                if login_input:
                    await page.fill('input[name="login"]', self._login)
                    await page.fill('input[name="password"]', self._password)
                    await page.click('button[type="submit"]')
                    await asyncio.sleep(random.uniform(5, 7))

                # 3. Переход к списку заказов
                await page.goto("https://advego.com/job/find/?job_type=1&job_type=2")
                await asyncio.sleep(random.uniform(4, 6))

                # 4. Поиск кнопки "Взять в работу"
                # Ищем кнопку именно по тексту, который виден на видео
                take_buttons = await page.query_selector_all('text="Взять в работу"')
                
                if take_buttons:
                    # Кликаем по первой доступной кнопке
                    await take_buttons[0].click()
                    await asyncio.sleep(3)
                    return "Успех: заказ взят!", 150.0
                
                return "Заказов с кнопкой 'Взять в работу' не найдено", 0.0

            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await page.screenshot(path="error.png") # Сохраняем скриншот для дебага
                return f"Ошибка при работе с Advego: {str(e)}", 0.0
            finally:
                await browser.close()
