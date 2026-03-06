import asyncio
from playwright.async_api import Page
from config.settings import BotSettings
from utils.selectors import Selectors
from utils.timing import OrderDelays
from utils.logger import get_logger

logger = get_logger()

class CartManager:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays = None):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def add_to_cart(self) -> bool:
        try:
            add_btn = self.page.locator(Selectors.ADD_TO_CART_BTN).first
            await add_btn.wait_for(state="visible", timeout=10000)
            await add_btn.click()
            await asyncio.sleep(2.0)
            try:
                await self.page.wait_for_selector(
                    ".woocommerce-notices-wrapper .woocommerce-message, a.added_to_cart",
                    timeout=5000,
                )
                logger.debug("Producto añadido al carrito ✓")
            except Exception:
                pass
            if self.delays:
                await self.delays.wait("add_to_cart")
            return True
        except Exception as e:
            logger.error("Failed to add to cart: %s", e)
            return False

    async def proceed_to_checkout(self) -> bool:
        cart_url = self.settings.store_url.rstrip("/") + Selectors.CART_PAGE_PATH
        logger.debug("Going to cart: %s", cart_url)
        await self.page.goto(cart_url, wait_until="domcontentloaded")
        await asyncio.sleep(1.5)
        try:
            checkout_btn = self.page.locator(Selectors.CART_PROCEED_CHECKOUT).first
            await checkout_btn.wait_for(state="visible", timeout=10000)
            await checkout_btn.click()
            logger.debug("Clicked 'Proceed to Checkout'")
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1.5)
            if self.delays:
                await self.delays.wait("before_checkout")
            return True
        except Exception as e:
            logger.error("Failed to proceed to checkout: %s", e)
            return False
