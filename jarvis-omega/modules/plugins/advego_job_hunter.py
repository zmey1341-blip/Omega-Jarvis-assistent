import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger("jarvis.plugins.advego_jobs")

class AdvegoJobHunter:
    def __init__(self, router):
        self._router = router
        self._login = "zmey1341@mail.ru"
        self._password = "Samsung777+"
        # Динамически определяем путь к папке static для сохранения скриншотов
        self._static_dir = Path(__file__).resolve().parents[2] / "static"

    async def hunt_and_execute(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                    "--no-zygote"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()

            try:
                logger.info("Переход на страницу авторизации Advego...")
                await page.goto("https://advego.com/login/", timeout=60000)
                
                # Ожидаем, пока прекратится активный сетевой обмен (страница полностью загрузится)
                await page.wait_for_load_state("networkidle")
                
                # Проверяем наличие формы авторизации. Если её нет — возможно, нужно переключить вкладку
                # Или страница заблокирована антиботом.
                try:
                    await page.wait_for_selector('input[name="email"]:visible', timeout=10000)
                except Exception:
                    logger.warning("[Advego] Видимое поле email не найдено за 10с. Проверяем вкладку 'Вход'...")
                    # Пытаемся тыкнуть на переключатель формы «Вход» на случай, если по дефолту открылась регистрация
                    login_tab = await page.query_selector('text="Вход"')
                    if login_tab and await login_tab.is_visible():
                        await login_tab.click()
                        await asyncio.sleep(2)

                # Заполнение данных формы
                await page.fill('input[name="email"]:visible', self._login)
                await page.fill('input[name="password"]:visible', self._password)
                await page.click('button[type="submit"]:visible')
                
                logger.info("Ожидание завершения авторизации...")
                try:
                    await page.wait_for_url("https://advego.com/", timeout=15000)
                except Exception:
                    await asyncio.sleep(5) 

                logger.info("Переход на страницу поиска заказов...")
                await page.goto("https://advego.com/job/find/?job_type=1&job_type=2", timeout=60000)
                
                try:
                    await page.wait_for_selector('.job_item', timeout=10000)
                except Exception:
                    logger.info("На странице нет доступных карточек заказов.")
                    return "Заказов пока нет", 0.0
                
                job_card = await page.query_selector('.job_item')
                if not job_card:
                    return "Заказов пока нет", 0.0

                take_button = await job_card.query_selector('a.job_take_link')
                if take_button:
                    await take_button.click()
                    logger.info("Кнопка 'Взять в работу' успешно нажата!")
                    return "Заказ успешно взят в работу!", 150.0 
                
                return "Доступны только тендеры, ждем свободный заказ", 0.0

            except Exception as e:
                logger.error(f"Ошибка в работе AdvegoJobHunter: {e}", exc_info=True)
                
                # Гвардейский блок: делаем скриншот экрана в случае падения
                if self._static_dir.exists():
                    screenshot_path = self._static_dir / "advego_error.png"
                    try:
                        await page.screenshot(path=str(screenshot_path))
                        logger.info(f"[Advego] Скриншот страницы ошибки сохранен: {screenshot_path}")
                    except Exception as screenshot_err:
                        logger.error(f"Не удалось сохранить скриншот: {screenshot_err}")
                
                return f"Сбой: {str(e)}", 0.0
            finally:
                await context.close()
                browser_process = browser.process
                await browser.close()
                if browser_process and browser_process.poll() is None:
                    try:
                        browser_process.kill()
                    except Exception:
                        pass
