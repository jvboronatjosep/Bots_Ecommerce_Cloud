import asyncio
import logging

from playwright.async_api import Page

from config.settings import BotSettings
from utils.logger import log_info
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("shopify_bot")


class CartManager:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays = None):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def add_to_cart(self) -> bool:
        add_btn = self.page.locator(Selectors.ADD_TO_CART_BTN).first
        try:
            await add_btn.wait_for(state="visible", timeout=10000)
            await add_btn.click()
            # Wait for cart drawer to open and button to become enabled
            await asyncio.sleep(3.0)
            if self.delays:
                await self.delays.wait("add_to_cart")
            log_info("Producto añadido al carrito [green]✓[/green]")
            return True
        except Exception as e:
            logger.error("Failed to add to cart: %s", e)
            return False

    async def proceed_to_checkout(self) -> bool:
        # Try checkout button in cart drawer first
        drawer_btn = self.page.locator(Selectors.CART_DRAWER_CHECKOUT).first
        try:
            await drawer_btn.wait_for(state="visible", timeout=8000)
            await drawer_btn.click()
            logger.debug("Clicked checkout in cart drawer")
            await self.page.wait_for_load_state("domcontentloaded")
            if self.delays:
                await self.delays.wait("before_checkout")
            return True
        except Exception:
            pass

        # Fallback: /cart page
        logger.debug("Cart drawer not available, going to /cart page")
        cart_url = self.settings.store_url.rstrip("/") + "/cart"
        await self.page.goto(cart_url, wait_until="domcontentloaded")
        await asyncio.sleep(1.0)

        checkout_btn = self.page.locator(Selectors.CART_PAGE_CHECKOUT).first
        try:
            await checkout_btn.wait_for(state="visible", timeout=15000)
            await checkout_btn.click()
            logger.debug("Clicked checkout on cart page")
            await self.page.wait_for_load_state("domcontentloaded")
            if self.delays:
                await self.delays.wait("before_checkout")
            return True
        except Exception as e:
            logger.error("Failed to proceed to checkout: %s", e)
            return False

    async def close_cart_drawer(self):
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except Exception:
            pass
