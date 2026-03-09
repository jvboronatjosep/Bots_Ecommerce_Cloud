import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Page

from config.settings import BotSettings
from core.payment_handler import PaymentHandler
from data.fake_customer import FakeCustomer
from utils.logger import log_info
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("shopify_bot")


@dataclass
class OrderResult:
    order_index: int
    success: bool
    order_number: Optional[str] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    customer_email: Optional[str] = None
    duration_seconds: float = 0.0


class CheckoutHandler:
    def __init__(self, page: Page, settings: BotSettings, customer: FakeCustomer, delays: OrderDelays):
        self.page = page
        self.settings = settings
        self.customer = customer
        self.delays = delays
        self.payment = PaymentHandler(page, settings, delays)

    async def complete_checkout(self, order_index: int) -> OrderResult:
        result = OrderResult(
            order_index=order_index, success=False, customer_email=self.customer.email
        )
        try:
            log_info("Paso [cyan]1[/cyan]/4: Datos personales")
            await self._fill_contact_info()
            log_info("Paso [cyan]2[/cyan]/4: Direccion")
            await self._fill_shipping_address()
            log_info("Paso [cyan]3[/cyan]/4: Envio")
            await self._wait_for_shipping_rates()
            await self._select_shipping_method()
            await self.delays.wait("before_payment")
            log_info("Paso [cyan]4[/cyan]/4: Pago")
            await self.payment.fill_payment_fields()
            await self._submit_order()

            order_number = await self._extract_order_confirmation()
            result.success = True
            result.order_number = order_number

        except Exception as e:
            result.error_message = str(e)
            logger.error("Checkout failed: %s", e)

        return result



    async def _fill_contact_info(self):
        logger.debug("Filling contact: %s", self.customer.email)
        # Wait for Shopify checkout to fully load (client-side redirects after cart)
        try:
            await self.page.wait_for_url("**/checkouts/**", timeout=20000)
        except Exception:
            logger.warning("wait_for_url checkouts timed out, current url: %s", self.page.url)
        await self.page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(1.5)
        logger.warning("Checkout page url before email fill: %s", self.page.url)
        email_input = self.page.locator(Selectors.EMAIL_INPUT).first
        await email_input.wait_for(state="visible", timeout=20000)
        await email_input.click()
        await self.delays.wait("email_before")
        await email_input.fill(self.customer.email)
        await self.page.keyboard.press("Tab")
        await self.delays.wait("email_after")



    async def _fill_shipping_address(self):
        logger.debug("Filling shipping address...")

        await self._select_dropdown(Selectors.COUNTRY, self.customer.country_code)
        await self.delays.wait("country_select")
        await self._fill_field(Selectors.FIRST_NAME, self.customer.first_name)
        await self.delays.wait("first_name")
        await self._fill_field(Selectors.LAST_NAME, self.customer.last_name)
        await self.delays.wait("last_name")
        await self._fill_field(Selectors.CITY, self.customer.city)
        await self.delays.wait("city")
        await self._select_dropdown(Selectors.PROVINCE, self.customer.province_code)
        await self.delays.wait("province")
        await self._fill_field(Selectors.ZIP_CODE, self.customer.zip_code)
        await self.delays.wait("zip_code")
        if self.customer.address2:
            await self._fill_field(Selectors.ADDRESS2, self.customer.address2)
            await self.delays.wait("address2")
        await self._fill_field(Selectors.ADDRESS1, self.customer.address1)
        await self.delays.wait("address1")




        await self.page.keyboard.press("Tab")
        await self.delays.wait("address_done")
        logger.debug("Shipping address filled")

    async def _fill_field(self, selector: str, value: str):
        locator = self.page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=5000)
            await locator.click()
            await locator.fill(value)
        except Exception as e:
            logger.warning("Could not fill %s: %s", selector, e)

    async def _select_dropdown(self, selector: str, value: str):
        select = self.page.locator(selector).first
        try:
            await select.wait_for(state="visible", timeout=5000)
            await select.select_option(value)
        except Exception as e:
            logger.warning("Could not select %s in %s: %s", value, selector, e)

    async def _wait_for_shipping_rates(self):
        logger.debug("Waiting for shipping rates...")
        # Wait for the pay button to be enabled — indicates shipping is resolved
        try:
            pay_btn = self.page.locator(Selectors.PAY_NOW_BTN).first
            await pay_btn.wait_for(state="visible", timeout=15000)
            logger.debug("Shipping rates loaded (pay button ready)")
        except Exception:
            logger.debug("Pay button not yet visible, continuing anyway")
            await asyncio.sleep(1.0)

    async def _select_shipping_method(self):
        # Shipping is auto-selected on this store; nothing to do
        logger.debug("Shipping method auto-selected")

    async def _submit_order(self):
        logger.debug("Submitting order...")
        pay_btn = self.page.locator(Selectors.PAY_NOW_BTN).first
        await pay_btn.wait_for(state="visible", timeout=10000)
        await self.delays.wait("before_pay_click")
        await pay_btn.click()
        logger.debug("Waiting for order confirmation...")

    async def _extract_order_confirmation(self) -> str:
        # Poll URL until it contains "thank-you" or "thank_you"
        for _ in range(120):  # max ~60s
            url = self.page.url
            if "thank-you" in url or "thank_you" in url:
                break
            await asyncio.sleep(0.5)
        else:
            title = await self.page.title()
            if "thank" not in title.lower() and "order" not in title.lower():
                logger.warning("Did not reach thank you page (url: %s)", self.page.url)
                return "unknown"

        # Try to extract order number from page
        for selector in [Selectors.ORDER_NUMBER, "p:has-text('#')", "[class*='order']"]:
            try:
                el = self.page.locator(selector).first
                await el.wait_for(state="visible", timeout=2000)
                text = await el.text_content()
                if text and text.strip():
                    return text.strip()
            except Exception:
                continue

        return "confirmed"
