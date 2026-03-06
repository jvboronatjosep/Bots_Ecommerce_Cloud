import asyncio
import gzip
import json
import logging
import random
import ssl
import urllib.request

import certifi

from playwright.async_api import Page

from config.settings import BotSettings
from utils.logger import log_info
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("shopify_bot")


class StoreNavigator:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays = None):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def bypass_password_page(self) -> bool:
        store_base = self.settings.store_url.rstrip("/")
        logger.debug("Navigating to store: %s", store_base)
        await self.page.goto(store_base, wait_until="domcontentloaded")
        await asyncio.sleep(1.0)

        current_url = self.page.url
        logger.debug("Current URL after initial navigation: %s", current_url)

        if "/password" not in current_url:
            logger.debug("No password page, store is open")
            return True

        logger.debug("Password page detected, bypassing via fetch POST...")
        password = self.settings.store_password
        result = await self.page.evaluate(f"""
            async () => {{
                const body = new URLSearchParams({{
                    form_type: 'storefront_password',
                    utf8: '✓',
                    password: {password!r}
                }});
                const resp = await fetch('/password', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: body.toString(),
                    redirect: 'follow'
                }});
                return {{ status: resp.status, url: resp.url }};
            }}
        """)
        logger.debug("Password POST result: %s", result)

        await self.page.goto(store_base + Selectors.COLLECTION_ALL, wait_until="domcontentloaded")
        await asyncio.sleep(1.0)

        current_url = self.page.url
        if "/password" in current_url:
            logger.error("Password bypass failed, still on password page")
            return False

        logger.debug("Password bypass successful, now at: %s", current_url)
        return True

    async def get_product_urls(self) -> list[str]:
        store_base = self.settings.store_url.rstrip("/")
        api_url = store_base + "/products.json?limit=250"
        logger.debug("Fetching products via JSON API: %s", api_url)

        # Extract cookies from browser context to use in Python HTTP request
        cookies = await self.page.context.cookies()
        cookie_header = "; ".join(
            f"{c['name']}={c['value']}" for c in cookies
        )

        def fetch_products():
            req = urllib.request.Request(
                api_url,
                headers={
                    "Accept": "application/json",
                    "Cookie": cookie_header,
                },
            )
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(req, context=ssl_ctx) as resp:
                raw = resp.read()
                encoding = resp.headers.get("Content-Encoding", "")
                if "gzip" in encoding:
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))

        data = await asyncio.get_event_loop().run_in_executor(None, fetch_products)

        if not data or "products" not in data:
            logger.error("JSON API returned no data: %s", data)
            return []

        product_urls = [
            store_base + "/products/" + p["handle"]
            for p in data["products"]
        ]
        logger.debug("Found %d unique products", len(product_urls))
        return product_urls

    async def navigate_to_product(self, product_url: str) -> bool:
        logger.debug("Navigating to product: %s", product_url)
        await self.page.goto(product_url, wait_until="domcontentloaded")
        if self.delays:
            await self.delays.wait("product_page")

        add_btn = self.page.locator(Selectors.ADD_TO_CART_BTN).first
        try:
            await add_btn.wait_for(state="visible", timeout=5000)
            log_info("Producto encontrado [green]✓[/green]")
            return True
        except Exception:
            logger.warning("Add to cart button not found on %s", product_url)
            return False

    async def select_random_variant(self):
        variant_selects = self.page.locator(Selectors.VARIANT_SELECT)
        count = await variant_selects.count()

        for i in range(count):
            select = variant_selects.nth(i)
            if await select.is_visible():
                options = select.locator("option")
                option_count = await options.count()
                if option_count > 1:
                    first_text = (await options.nth(0).text_content()).strip().lower()
                    start = 1 if "select" in first_text or "choose" in first_text else 0
                    if start < option_count:
                        idx = random.randint(start, option_count - 1)
                        value = await options.nth(idx).get_attribute("value")
                        if value:
                            await select.select_option(value)
                            await asyncio.sleep(0.3)
