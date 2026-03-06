import asyncio
import logging

from playwright.async_api import Page

from config.settings import BotSettings
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("ps17_bot")


class CartManager:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def add_to_cart(self) -> bool:
        try:
            btn = self.page.locator(Selectors.ADD_TO_CART_BTN).first
            await btn.wait_for(state="visible", timeout=8000)
            await self.delays.wait("add_to_cart")
            await btn.click()
            await asyncio.sleep(2.5)
            logger.debug("Clicked 'Add to Cart'")
            return True
        except Exception as e:
            logger.warning("Could not add to cart: %s", e)
            return False

    async def proceed_to_checkout(self) -> bool:
        store_base = self.settings.store_url.rstrip("/")
        cart_url = f"{store_base}/index.php?controller=cart&action=show"
        logger.debug("Going to cart: %s", cart_url)

        await self.page.goto(cart_url, wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        try:
            btn = self.page.locator(Selectors.CART_PROCEED).first
            await btn.wait_for(state="visible", timeout=8000)
            await btn.click()
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2.0)
            logger.debug("Clicked proceed to checkout")
            return True
        except Exception as e:
            logger.warning("Could not proceed to checkout: %s", e)
            return False
