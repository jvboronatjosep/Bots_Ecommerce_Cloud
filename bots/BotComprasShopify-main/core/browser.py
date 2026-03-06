import os
import logging

from playwright.async_api import Browser, BrowserContext, Page
from camoufox.async_api import AsyncNewBrowser
from playwright.async_api import async_playwright

from config.settings import BotSettings

logger = logging.getLogger("shopify_bot")


class BrowserManager:
    def __init__(self, settings: BotSettings):
        self.settings = settings
        self._playwright = None
        self._browser: Browser | None = None
        self._stored_cookies: list = []

    async def launch(self) -> Browser:
        self._playwright = await async_playwright().start()
        self._browser = await AsyncNewBrowser(
            self._playwright,
            headless=self.settings.headless,
        )
        logger.debug("Camoufox browser launched (headless=%s)", self.settings.headless)
        return self._browser

    async def store_cookies(self, context: BrowserContext):
        self._stored_cookies = await context.cookies()

    async def new_context(self) -> tuple[BrowserContext, Page]:
        context = await self._browser.new_context(
            extra_http_headers={"Accept-Encoding": "identity"},
        )
        context.set_default_timeout(self.settings.browser_timeout)

        # Inject stored cookies (password bypass) if available
        if self._stored_cookies:
            await context.add_cookies(self._stored_cookies)

        page = await context.new_page()
        return context, page

    async def take_screenshot(self, page: Page, name: str) -> str | None:
        if not self.settings.screenshot_on_error:
            return None
        os.makedirs(self.settings.screenshots_dir, exist_ok=True)
        path = os.path.join(self.settings.screenshots_dir, f"{name}.png")
        await page.screenshot(path=path, full_page=True)
        logger.debug("Screenshot saved: %s", path)
        return path

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.debug("Browser closed")
