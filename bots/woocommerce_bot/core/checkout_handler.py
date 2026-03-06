import asyncio
import re
from dataclasses import dataclass
from typing import Optional
from playwright.async_api import Page
from config.settings import BotSettings
from data.fake_customer import FakeCustomer
from utils.selectors import Selectors
from utils.timing import OrderDelays
from utils.logger import get_logger

logger = get_logger()

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

    async def complete_checkout(self, order_index: int, total_orders: int = 1) -> OrderResult:
        result = OrderResult(order_index=order_index, success=False, customer_email=self.customer.email)
        try:
            checkout_url = self.settings.store_url.rstrip("/") + "/checkout"
            if "/checkout" not in self.page.url:
                await self.page.goto(checkout_url, wait_until="domcontentloaded")
                await asyncio.sleep(2.0)
            await self._fill_billing_form()
            await self._select_payment()
            await self._place_order()
            order_number = await self._extract_order_number()
            result.success = True
            result.order_number = order_number
            logger.order_done(order_index, total_orders, order_number)
        except Exception as e:
            result.error_message = str(e)
            logger.error("[Order %d/%d] Checkout fallido: %s", order_index, total_orders, e)
            await self._screenshot(f"error_step_{order_index}")
        return result

    async def _fill_billing_form(self):
        logger.paso(1, 4, "Datos personales")
        await asyncio.sleep(1.0)
        await self._fill(Selectors.CHECKOUT_FIRSTNAME, self.customer.first_name)
        await self.delays.wait("first_name")
        await self._fill(Selectors.CHECKOUT_LASTNAME, self.customer.last_name)
        await self.delays.wait("last_name")
        await self._fill(Selectors.CHECKOUT_EMAIL, self.customer.email)
        await self.delays.wait("email_after")
        await self._fill(Selectors.CHECKOUT_PHONE, self.customer.phone)
        logger.paso(2, 4, "Dirección")
        await self._fill(Selectors.CHECKOUT_ADDRESS1, self.customer.address1)
        await self.delays.wait("address1")
        await self._fill(Selectors.CHECKOUT_CITY, self.customer.city)
        await self.delays.wait("city")
        await self._fill(Selectors.CHECKOUT_POSTCODE, self.customer.zip_code)
        await self.delays.wait("zip_code")
        await self._select2_country("ES")
        await asyncio.sleep(0.8)
        await self._fill_state()
        await self.delays.wait("address_done")
        await self._fill_dni()
        await self._screenshot("billing_filled")

    async def _select2_country(self, country_code: str):
        try:
            result = await self.page.evaluate(f"""
                () => {{
                    const sel = document.querySelector('{Selectors.CHECKOUT_COUNTRY}');
                    if (!sel) return 'no_country_field';
                    sel.value = '{country_code}';
                    sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                    if (typeof jQuery !== 'undefined') jQuery(sel).trigger('change');
                    return 'ok';
                }}
            """)
            logger.debug("Country select: %s", result)
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.warning("Could not set country: %s", e)

    async def _fill_state(self):
        try:
            state_result = await self.page.evaluate(f"""
                () => {{
                    const sel = document.querySelector('{Selectors.CHECKOUT_STATE}');
                    if (!sel) return 'not_found';
                    if (sel.tagName === 'SELECT') {{
                        const code = '{self.customer.province_code}';
                        const city = '{self.customer.city}'.toLowerCase();
                        const opts = Array.from(sel.options).filter(o => o.value);
                        const match = opts.find(o =>
                            o.value.toLowerCase() === code.toLowerCase() ||
                            o.text.toLowerCase().includes(city)
                        ) || opts[0];
                        if (match) {{
                            sel.value = match.value;
                            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                            if (typeof jQuery !== 'undefined') jQuery(sel).trigger('change');
                            return 'select:' + match.value;
                        }}
                    }} else {{
                        sel.value = '{self.customer.city}';
                        sel.dispatchEvent(new Event('input', {{bubbles: true}}));
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'input:ok';
                    }}
                    return 'no_match';
                }}
            """)
            logger.debug("State fill: %s", state_result)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning("Could not fill state: %s", e)

    async def _fill_dni(self):
        try:
            result = await self.page.evaluate(f"""
                () => {{
                    const ids = ['#billing_vat','#billing_dni','#billing_nif','#billing_id_number','#billing_cfpiva'];
                    for (const s of ids) {{
                        const el = document.querySelector(s);
                        if (el) {{
                            el.value = '{self.customer.dni}';
                            el.dispatchEvent(new Event('input', {{bubbles: true}}));
                            el.dispatchEvent(new Event('change', {{bubbles: true}}));
                            return 'filled:' + s;
                        }}
                    }}
                    return 'not_found';
                }}
            """)
            logger.debug("DNI fill: %s", result)
        except Exception as e:
            logger.warning("DNI fill error: %s", e)

    async def _select_payment(self):
        logger.paso(3, 4, "Envío")
        logger.paso(4, 4, "Pago")
        await asyncio.sleep(1.0)
        await self.page.evaluate("""
            () => {
                const opts = document.querySelectorAll('input[name="payment_method"]');
                if (opts.length > 0) {
                    opts[0].click();
                    opts[0].dispatchEvent(new Event('change', {bubbles: true}));
                }
            }
        """)
        await asyncio.sleep(0.8)
        terms_result = await self.page.evaluate("""
            () => {
                const cb = document.querySelector('#terms');
                if (cb && !cb.checked) { cb.click(); return 'terms_checked'; }
                return cb ? 'already_checked' : 'not_found';
            }
        """)
        logger.debug("Terms checkbox: %s", terms_result)
        await asyncio.sleep(0.5)

    async def _place_order(self):
        logger.debug("Placing order...")
        await self.delays.wait("before_pay_click")
        place_btn = self.page.locator(Selectors.PAYMENT_PLACE_ORDER).first
        await place_btn.wait_for(state="visible", timeout=10000)
        for _ in range(20):
            if not await place_btn.is_disabled():
                break
            logger.debug("Place order button still disabled...")
            await asyncio.sleep(0.5)
        await place_btn.click()
        logger.debug("Order submitted — waiting for confirmation page...")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3.0)

    async def _extract_order_number(self) -> str:
        for _ in range(60):
            url = self.page.url
            if "order-received" in url or "pedido-recibido" in url:
                break
            await asyncio.sleep(1.0)
        else:
            logger.warning("Did not reach order-received page (url: %s)", self.page.url)
            return "unknown"
        logger.debug("Reached confirmation page: %s", self.page.url)
        match = re.search(r"order-received/(\d+)", self.page.url)
        if match:
            return f"#{match.group(1)}"
        try:
            order_el = self.page.locator(Selectors.ORDER_NUMBER).first
            text = await order_el.inner_text()
            return f"#{text.strip()}"
        except Exception:
            return "confirmed"

    async def _fill(self, selector: str, value: str):
        try:
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=5000)
            await locator.click()
            await locator.fill(value)
        except Exception as e:
            logger.warning("Could not fill '%s': %s", selector, e)

    async def _screenshot(self, name: str):
        try:
            import os
            os.makedirs("screenshots", exist_ok=True)
            await self.page.screenshot(path=f"screenshots/{name}.png", full_page=True)
            logger.debug("Screenshot: screenshots/%s.png", name)
        except Exception:
            pass
