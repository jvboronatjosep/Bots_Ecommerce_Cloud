import asyncio
import logging
import random
import re
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Page

from config.settings import BotSettings
from data.fake_customer import FakeCustomer
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("ps17_bot")


@dataclass
class OrderResult:
    order_index: int
    success: bool
    order_number: Optional[str] = None
    error_message: Optional[str] = None
    customer_email: Optional[str] = None
    duration_seconds: float = 0.0


class CheckoutHandler:
    def __init__(self, page: Page, settings: BotSettings, customer: FakeCustomer, delays: OrderDelays):
        self.page = page
        self.settings = settings
        self.customer = customer
        self.delays = delays

    async def complete_checkout(self, order_index: int, total_orders: int = 0) -> OrderResult:
        result = OrderResult(order_index=order_index, success=False, customer_email=self.customer.email)
        try:
            await self._step1_personal_info()
            await self._step2_address()
            await self._step3_delivery()
            await self._step4_payment()

            order_number = await self._extract_order_confirmation()
            result.success = True
            result.order_number = order_number
            logger.debug(
                "[green][Order %d/%d] COMPLETADO - Ref: %s ✓[/green]",
                order_index, total_orders, order_number,
            )

        except Exception as e:
            result.error_message = str(e)
            logger.error("[Order %d/%d] Checkout fallido: %s", order_index, total_orders, e)
            await self._screenshot(f"error_{order_index}")

        return result

    # ── Step 1: DATOS PERSONALES ──────────────────────────────────────────────
    async def _step1_personal_info(self):
        logger.debug("[cyan]Paso 1[/cyan]/4: Datos personales")

        if "/pedido" not in self.page.url and "controller=order" not in self.page.url:
            await self.page.goto(
                self.settings.store_url.rstrip("/") + "/index.php?controller=order",
                wait_until="domcontentloaded"
            )
            await asyncio.sleep(2.0)

        # Gender
        try:
            gender_sel = Selectors.GUEST_GENDER_MRS if random.random() < 0.5 else Selectors.GUEST_GENDER_MR
            await self.page.evaluate(f'() => {{ const r = document.querySelector("{gender_sel}"); if(r) r.click(); }}')
            await asyncio.sleep(0.3)
        except Exception:
            pass

        await self._fill(Selectors.GUEST_FIRSTNAME, self.customer.first_name)
        await self.delays.wait("first_name")
        await self._fill(Selectors.GUEST_LASTNAME, self.customer.last_name)
        await self.delays.wait("last_name")
        await self._fill(Selectors.GUEST_EMAIL, self.customer.email)
        await self.delays.wait("email_after")

        # Required checkboxes
        await self.page.evaluate("""
            () => document.querySelectorAll(
                '#checkout-personal-information-step input[type="checkbox"]'
            ).forEach(cb => { if (cb.required && !cb.checked) cb.click(); })
        """)
        await asyncio.sleep(0.5)

        await self.page.evaluate("""
            () => {
                const btn = document.querySelector(
                    '#checkout-personal-information-step button[name="continue"]'
                );
                if (btn) btn.click();
            }
        """)
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2.0)

    # ── Step 2: DIRECCIONES ───────────────────────────────────────────────────
    async def _step2_address(self):
        logger.debug("[cyan]Paso 2[/cyan]/4: Direccion")
        await asyncio.sleep(1.5)

        await self._js_fill("field-address1", self.customer.address1)
        await self.delays.wait("address1")
        await self._js_fill("field-postcode", self.customer.zip_code)
        await self.delays.wait("zip_code")
        await self._js_fill("field-city", self.customer.city)
        await self.delays.wait("city")
        await self._js_fill("field-phone", self.customer.phone)
        await self.delays.wait("address_done")
        await self._js_fill("field-dni", self.customer.dni)
        await asyncio.sleep(0.3)

        # Province dropdown
        state_id = await self._resolve_state_id()
        if state_id:
            await self.page.evaluate(f"""
                () => {{
                    const sel = document.getElementById('field-id_state');
                    if (sel) {{
                        sel.value = '{state_id}';
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }}
            """)
            await asyncio.sleep(0.5)
            logger.debug("Province selected: %s", state_id)

        # Click CONTINUAR
        try:
            btn = self.page.locator("#checkout-addresses-step button[name='confirm-addresses']").first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            logger.debug("Step 2 CONTINUAR clicked")
        except Exception:
            await self.page.evaluate("""
                () => {
                    const btn = document.querySelector('#checkout-addresses-step button[type="submit"]');
                    if (btn) btn.click();
                }
            """)

        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2.0)

    # ── Step 3: MÉTODO DE ENVÍO ───────────────────────────────────────────────
    async def _step3_delivery(self):
        logger.debug("[cyan]Paso 3[/cyan]/4: Envio")
        await asyncio.sleep(1.5)

        await self.page.evaluate("""
            () => {
                const radios = document.querySelectorAll('input[type="radio"][name*="delivery"]');
                if (radios.length > 0) radios[0].click();
            }
        """)
        await asyncio.sleep(0.5)

        try:
            btn = self.page.locator("#checkout-delivery-step button[name='confirmDeliveryOption']").first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            logger.debug("Step 3 CONTINUAR clicked")
        except Exception:
            await self.page.evaluate("""
                () => {
                    const btn = document.querySelector('#checkout-delivery-step button[type="submit"]');
                    if (btn) btn.click();
                }
            """)

        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2.0)

    # ── Step 4: PAGO ──────────────────────────────────────────────────────────
    async def _step4_payment(self):
        logger.debug("[cyan]Paso 4[/cyan]/4: Pago")
        await asyncio.sleep(1.5)

        # PS1.7: payment options are radio buttons, not input.payment-option
        payment_selected = await self.page.evaluate("""
            () => {
                // Try PS8 style first
                const ps8 = document.querySelectorAll('input.payment-option');
                if (ps8.length > 0) { ps8[0].click(); return 'ps8:' + ps8[0].id; }

                // PS1.7: radio buttons with any name
                const radios = document.querySelectorAll(
                    'input[type="radio"][name*="payment"], ' +
                    'input[type="radio"][id*="payment"], ' +
                    '#payment-option-1, #payment-option-2, ' +
                    '.payment-options input[type="radio"]'
                );
                if (radios.length > 0) { radios[0].click(); return 'radio:' + radios[0].id; }

                // Last resort: any visible radio in payment section
                const allRadios = document.querySelectorAll('#checkout-payment-step input[type="radio"]');
                if (allRadios.length > 0) { allRadios[0].click(); return 'any_radio:' + allRadios[0].id; }

                return 'not_found';
            }
        """)
        logger.debug("Payment option selected: %s", payment_selected)
        await asyncio.sleep(1.0)

        # Accept terms (try both PS8 and PS1.7 selectors)
        await self.page.evaluate("""
            () => {
                const selectors = [
                    'input[name="conditions_to_approve[terms-and-conditions]"]',
                    'input#conditions_to_approve',
                    'input[name="cgv"]',
                    '#payment-confirmation input[type="checkbox"]',
                    '#checkout-payment-step input[type="checkbox"]',
                ];
                for (const sel of selectors) {
                    const cb = document.querySelector(sel);
                    if (cb && !cb.checked) { cb.click(); return; }
                }
            }
        """)
        logger.debug("Terms accepted")
        await asyncio.sleep(0.5)

        # Place order button — try multiple selectors
        place_btn = None
        for sel in [
            Selectors.PAYMENT_PLACE_ORDER,
            "button.btn-primary[type='submit']",
            "#payment-confirmation button",
            "button#payment-confirmation--proceed-button",
        ]:
            try:
                loc = self.page.locator(sel).first
                await loc.wait_for(state="visible", timeout=3000)
                place_btn = loc
                logger.debug("Place order button found: %s", sel)
                break
            except Exception:
                pass

        if not place_btn:
            raise Exception("Place order button not found")

        for _ in range(10):
            if not await place_btn.is_disabled():
                break
            await asyncio.sleep(0.5)

        await self.delays.wait("before_pay_click")
        await place_btn.click()
        logger.debug("Order submitted")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3.0)

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def _fill(self, selector: str, value: str):
        try:
            loc = self.page.locator(selector).first
            await loc.wait_for(state="visible", timeout=5000)
            await loc.click()
            await loc.fill(value)
        except Exception as e:
            logger.warning("Could not fill '%s': %s", selector, e)

    async def _js_fill(self, field_id: str, value: str):
        value_escaped = value.replace("'", "\\'")
        await self.page.evaluate(f"""
            () => {{
                const el = document.getElementById('{field_id}');
                if (!el) return;
                el.focus();
                el.value = '{value_escaped}';
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                el.blur();
            }}
        """)

    async def _resolve_state_id(self) -> str:
        result = await self.page.evaluate(f"""
            () => {{
                const sel = document.getElementById('field-id_state');
                if (!sel) return null;
                const city = '{self.customer.city}'.toLowerCase();
                const opts = Array.from(sel.options).filter(o => o.value && o.value !== '0');
                const match = opts.find(o => o.text.toLowerCase().includes(city));
                if (match) return match.value;
                return opts.length > 0 ? opts[0].value : null;
            }}
        """)
        return result or ""

    async def _screenshot(self, name: str):
        try:
            import os
            os.makedirs("screenshots", exist_ok=True)
            await self.page.screenshot(path=f"screenshots/{name}.png", full_page=True)
            logger.debug("Screenshot: screenshots/%s.png", name)
        except Exception:
            pass

    async def _extract_order_confirmation(self) -> str:
        for _ in range(60):
            if "controller=order-confirmation" in self.page.url or "confirmacion-pedido" in self.page.url:
                break
            await asyncio.sleep(1.0)
        else:
            logger.warning("Did not reach confirmation page (url: %s)", self.page.url)
            return "unknown"

        logger.debug("Reached confirmation page: %s", self.page.url)
        match = re.search(r"id_order=(\d+)", self.page.url)
        return f"#{match.group(1)}" if match else "confirmed"
