import asyncio
import random
from playwright.async_api import Page
from config.settings import BotSettings
from utils.selectors import Selectors
from utils.timing import OrderDelays
from utils.logger import get_logger

logger = get_logger()

class StoreNavigator:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays = None):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def get_product_urls(self) -> list[str]:
        store_base = self.settings.store_url.rstrip("/")
        collection_url = store_base + Selectors.COLLECTION_ALL
        logger.debug("Fetching products from: %s", collection_url)
        await self.page.goto(collection_url, wait_until="domcontentloaded")
        await asyncio.sleep(2.0)
        title = await self.page.title()
        logger.debug("Shop page: '%s' | URL: %s", title, self.page.url)

        selectors_to_try = [
            "ul.products li.product a.woocommerce-loop-product__link",
            "ul.products li.product a.woocommerce-LoopProduct-link",
            ".products .product a[href*='product']",
            ".products .product a[href*='producto']",
            "a.product_type_simple",
            "a.product_type_variable",
        ]
        urls = []
        domain = self.settings.store_url.split("//")[1].split("/")[0]
        for sel in selectors_to_try:
            links = await self.page.locator(sel).all()
            if links and not urls:
                for link in links:
                    href = await link.get_attribute("href")
                    if href and href not in urls and domain in href:
                        urls.append(href)
            logger.debug("Selector '%s' found %d elements", sel, len(links))

        if not urls:
            await self.page.screenshot(path="products_debug.png", full_page=True)
            logger.warning("No products found — screenshot saved to products_debug.png")

        urls = [u for u in dict.fromkeys(urls) if "/product/" in u or "/producto/" in u or "/?p=" in u]
        logger.debug("Productos encontrados: %d", len(urls))
        return urls

    async def navigate_to_product(self, product_url: str) -> bool:
        await self.page.goto(product_url, wait_until="domcontentloaded")
        if self.delays:
            await self.delays.wait("product_page")
        try:
            add_btn = self.page.locator(Selectors.ADD_TO_CART_BTN).first
            await add_btn.wait_for(state="visible", timeout=8000)
            logger.debug("Producto encontrado ✓")
            return True
        except Exception:
            logger.warning("Botón 'Añadir al carrito' no encontrado en %s", product_url)
            return False

    async def select_random_variant(self):
        try:
            selects = self.page.locator(Selectors.VARIANT_SELECT)
            count = await selects.count()
            for i in range(count):
                sel = selects.nth(i)
                options = await sel.locator("option").all()
                valid_options = [await o.get_attribute("value") for o in options]
                valid_options = [v for v in valid_options if v and v.strip() != ""]
                if valid_options:
                    chosen = random.choice(valid_options)
                    await sel.select_option(chosen)
                    await asyncio.sleep(0.6)
                    logger.debug("Selected variant: %s", chosen)
            if count > 0:
                await asyncio.sleep(1.0)
        except Exception as e:
            logger.warning("Variant selection error: %s", e)
