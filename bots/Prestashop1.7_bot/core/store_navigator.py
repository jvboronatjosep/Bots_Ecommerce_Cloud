import asyncio
import logging
import random

from playwright.async_api import Page

from config.settings import BotSettings
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("ps17_bot")


class StoreNavigator:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays = None):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def get_product_urls(self) -> list[str]:
        store_base = self.settings.store_url.rstrip("/")
        url = store_base + Selectors.COLLECTION_PATH
        logger.debug("Fetching products from: %s", url)

        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2.5)

        title = await self.page.title()
        logger.debug("Collection page: '%s'", title)

        selectors_to_try = [
            "a.product-thumbnail",
            "a.thumbnail.product-thumbnail",
            ".product-miniature a.thumbnail",
            "article.product-miniature a",
            ".products article a",
        ]

        urls = []
        domain = self.settings.store_url.split("//")[1].split("/")[0]

        for sel in selectors_to_try:
            links = await self.page.locator(sel).all()
            logger.debug("Selector '%s' found %d elements", sel, len(links))
            if links and not urls:
                for link in links:
                    href = await link.get_attribute("href")
                    if href and domain in href and href not in urls:
                        urls.append(href)

        if not urls:
            await self.page.screenshot(path="screenshots/products_debug.png", full_page=True)
            logger.warning("No products found — screenshot saved")

        logger.debug("Productos encontrados: [green]%d[/green]", len(urls))
        if urls:
            logger.debug("Sample URLs: %s", urls[:3])
        return urls

    async def navigate_to_product(self, product_url: str) -> bool:
        logger.debug("Navigating to product: %s", product_url)
        await self.page.goto(product_url, wait_until="domcontentloaded")
        if self.delays:
            await self.delays.wait("product_page")

        try:
            add_btn = self.page.locator(Selectors.ADD_TO_CART_BTN).first
            await add_btn.wait_for(state="visible", timeout=8000)
            return True
        except Exception:
            logger.warning("Add to cart button not found on %s", product_url)
            return False

    async def select_random_variant(self):
        """Select random variant from <select> dropdowns."""
        try:
            selects = self.page.locator(Selectors.VARIANT_SELECT)
            count = await selects.count()
            if count == 0:
                logger.debug("No variant selects found, proceeding as-is")
                return

            for i in range(count):
                sel = selects.nth(i)
                try:
                    options = await sel.locator("option").all()
                    valid = []
                    for opt in options:
                        val = await opt.get_attribute("value")
                        if val and val not in ("", "0"):
                            valid.append(val)
                    if valid:
                        chosen = random.choice(valid)
                        await sel.select_option(value=chosen)
                        await asyncio.sleep(0.5)
                        logger.debug("Selected variant: %s", chosen)
                except Exception as e:
                    logger.warning("Could not select variant %d: %s", i, e)

        except Exception as e:
            logger.warning("Variant selection error: %s", e)
