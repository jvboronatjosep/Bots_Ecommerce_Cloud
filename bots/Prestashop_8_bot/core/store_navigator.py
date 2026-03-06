import asyncio
import logging
import random

from playwright.async_api import Page

from config.settings import BotSettings
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("prestashop_bot")


class StoreNavigator:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays = None):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def get_product_urls(self) -> list[str]:
        """Scrape product URLs from the public /2-inicio page. No login needed."""
        store_base = self.settings.store_url.rstrip("/")
        collection_url = store_base + Selectors.COLLECTION_ALL
        logger.debug("Fetching products from: %s", collection_url)

        await self.page.goto(collection_url, wait_until="domcontentloaded")
        await asyncio.sleep(2.0)

        title = await self.page.title()
        logger.debug("Collection page: '%s' | URL: %s", title, self.page.url)

        # Try selectors in order, use first one that finds results
        selectors_to_try = [
            "a.product-thumbnail",
            "a.thumbnail.product-thumbnail",
            ".product-miniature a.thumbnail",
            "article.product-miniature a",
            ".products article a",
            "a[href*='/men/'], a[href*='/women/'], a[href*='/art/'], a[href*='/home-accessories/']",
        ]

        urls = []
        for sel in selectors_to_try:
            links = await self.page.locator(sel).all()
            if links and not urls:
                for link in links:
                    href = await link.get_attribute("href")
                    if href and href not in urls and self.settings.store_url.split("//")[1].split("/")[0] in href:
                        urls.append(href)
            logger.debug("Selector '%s' found %d elements", sel, len(links))

        if not urls:
            await self.page.screenshot(path="products_debug.png", full_page=True)
            logger.warning("No products found — screenshot saved to products_debug.png")

        logger.debug("Total products found: %d", len(urls))
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
        """Select random radio-button variants (size, color)."""
        try:
            variant_inputs = self.page.locator(Selectors.VARIANT_RADIO)
            count = await variant_inputs.count()

            if count == 0:
                logger.debug("No variants found, proceeding as-is")
                return

            names_seen = set()
            for i in range(count):
                inp = variant_inputs.nth(i)
                name = await inp.get_attribute("name")
                if name not in names_seen:
                    names_seen.add(name)
                    group = self.page.locator(f"input[type='radio'][name='{name}']")
                    group_count = await group.count()
                    if group_count > 0:
                        idx = random.randint(0, group_count - 1)
                        try:
                            await group.nth(idx).click()
                            await asyncio.sleep(0.4)
                            logger.debug("Selected variant %s option %d", name, idx)
                        except Exception as e:
                            logger.warning("Could not click variant %s: %s", name, e)

        except Exception as e:
            logger.warning("Variant selection error: %s", e)
