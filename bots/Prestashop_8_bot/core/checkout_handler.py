import asyncio
import logging
import random
import re
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Page
from rich.console import Console

from config.settings import BotSettings
from data.fake_customer import FakeCustomer
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("prestashop_bot")
console = Console(force_terminal=True)


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

    async def complete_checkout(self, order_index: int) -> OrderResult:
        result = OrderResult(
            order_index=order_index, success=False, customer_email=self.customer.email
        )
        try:
            await self._step1_personal_info()
            await self._step2_address()
            await self._step3_delivery()
            await self._step4_payment()

            order_number = await self._extract_order_confirmation()
            result.success = True
            result.order_number = order_number
            console.print(f"[bold green][LOG] [Order {order_index}] COMPLETADO - Ref: {order_number} ✓[/bold green]")

        except Exception as e:
            result.error_message = str(e)
            logger.error("[Order %d] Checkout failed: %s", order_index, e)
            await self._screenshot(f"error_step_{order_index}")

        return result

    # ── Step 1: DATOS PERSONALES ─────────────────────────────────────────────
    async def _step1_personal_info(self):
        console.print("[bold white][LOG][/bold white] Paso [cyan]1/4[/cyan]: Datos personales")

        if "/pedido" not in self.page.url:
            await self.page.goto(self.settings.store_url.rstrip("/") + "/pedido", wait_until="domcontentloaded")
            await asyncio.sleep(2.0)

        # Gender radio
        try:
            gender_sel = Selectors.GUEST_GENDER_MRS if random.random() < 0.5 else Selectors.GUEST_GENDER_MR
            await self.page.evaluate(f'() => {{ const r = document.querySelector("{gender_sel}"); if(r) r.click(); }}')
            await asyncio.sleep(0.3)
        except Exception:
            pass

        await self._fill_field(Selectors.GUEST_FIRSTNAME, self.customer.first_name)
        await self.delays.wait("first_name")
        await self._fill_field(Selectors.GUEST_LASTNAME, self.customer.last_name)
        await self.delays.wait("last_name")
        await self._fill_field(Selectors.GUEST_EMAIL, self.customer.email)
        await self.delays.wait("email_after")

        # Mark required checkboxes only (psgdpr + customer_privacy)
        await self.page.evaluate("""
            () => {
                document.querySelectorAll(
                    '#checkout-personal-information-step input[type="checkbox"]'
                ).forEach(cb => { if (cb.required && !cb.checked) cb.click(); });
            }
        """)
        await asyncio.sleep(0.5)

        # JS click — button may be considered hidden by Playwright
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
        logger.debug("Step 1 done")

    # ── Step 2: DIRECCIONES ──────────────────────────────────────────────────
    async def _step2_address(self):
        console.print("[bold white][LOG][/bold white] Paso [cyan]2/4[/cyan]: Direccion")
        await asyncio.sleep(1.5)

        # Read real state IDs from the dropdown on first use
        state_id = await self._resolve_state_id()
        logger.debug("Resolved state_id for %s: %s", self.customer.city, state_id)

        await self._js_fill("field-address1", self.customer.address1)
        await self.delays.wait("address1")
        await self._js_fill("field-postcode", self.customer.zip_code)
        await self.delays.wait("zip_code")
        await self._js_fill("field-city", self.customer.city)
        await self.delays.wait("city")
        await self._js_fill("field-phone", self.customer.phone)
        await self.delays.wait("address_done")

        # Fill DNI — try multiple possible field IDs
        dni_filled = await self.page.evaluate(f"""
            () => {{
                // Try common IDs for DNI field
                const ids = ['field-dni', 'field-id_number', 'field-vat_number'];
                for (const id of ids) {{
                    const el = document.getElementById(id);
                    if (el) {{
                        el.focus();
                        el.value = '{self.customer.dni}';
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        el.blur();
                        return 'filled:' + id;
                    }}
                }}
                // Fallback: find by label text "identificacion" or "fiscal"
                const labels = Array.from(document.querySelectorAll('label'));
                const dniLabel = labels.find(l => 
                    l.textContent.toLowerCase().includes('fiscal') || 
                    l.textContent.toLowerCase().includes('identificaci')
                );
                if (dniLabel) {{
                    const forId = dniLabel.getAttribute('for');
                    const el = forId ? document.getElementById(forId) : null;
                    if (el) {{
                        el.value = '{self.customer.dni}';
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'filled_via_label:' + forId;
                    }}
                }}
                return 'not_found';
            }}
        """)
        logger.debug("DNI fill result: %s (value: %s)", dni_filled, self.customer.dni)
        await asyncio.sleep(0.3)

        # Select Estado (province) dropdown
        if state_id:
            state_selected = await self.page.evaluate(f"""
                () => {{
                    const sel = document.getElementById('field-id_state');
                    if (!sel) return 'no_state_field';
                    const opt = sel.querySelector('option[value="{state_id}"]');
                    if (opt) {{
                        sel.value = '{state_id}';
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'ok:{state_id}';
                    }}
                    return 'option_not_found';
                }}
            """)
            logger.debug("Estado selection: %s", state_selected)
            await asyncio.sleep(0.5)

        await self._screenshot("step2_filled")

        # Click CONTINUAR
        try:
            btn = self.page.locator("#checkout-addresses-step button[name='confirm-addresses']").first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            logger.debug("Step 2 CONTINUAR clicked via Playwright")
        except Exception:
            await self.page.evaluate("""
                () => {
                    const btn = document.querySelector(
                        '#checkout-addresses-step button[name="confirm-addresses"], ' +
                        '#checkout-addresses-step button[type="submit"]'
                    );
                    if (btn) btn.click();
                }
            """)
            logger.debug("Step 2 CONTINUAR clicked via JS fallback")

        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2.0)
        await self._screenshot("after_step2")

    # ── Step 3: MÉTODO DE ENVÍO ──────────────────────────────────────────────
    async def _step3_delivery(self):
        console.print("[bold white][LOG][/bold white] Paso [cyan]3/4[/cyan]: Envio")
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
            logger.debug("Step 3 CONTINUAR clicked via Playwright")
        except Exception:
            await self.page.evaluate("""
                () => {
                    const btn = document.querySelector(
                        '#checkout-delivery-step button[name="confirmDeliveryOption"], ' +
                        '#checkout-delivery-step button[type="submit"]'
                    );
                    if (btn) btn.click();
                }
            """)
            logger.debug("Step 3 CONTINUAR clicked via JS fallback")

        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2.0)
        await self._screenshot("after_step3")

    # ── Step 4: PAGO ─────────────────────────────────────────────────────────
    async def _step4_payment(self):
        console.print("[bold white][LOG][/bold white] Paso [cyan]4/4[/cyan]: Pago")
        await asyncio.sleep(1.5)

        await self.page.evaluate("""
            () => {
                const opts = document.querySelectorAll('input.payment-option');
                if (opts.length > 0) opts[0].click();
            }
        """)
        logger.debug("Payment option selected")
        await asyncio.sleep(1.0)

        await self.page.evaluate("""
            () => {
                const cb = document.querySelector(
                    'input[name="conditions_to_approve[terms-and-conditions]"]'
                );
                if (cb && !cb.checked) cb.click();
            }
        """)
        logger.debug("Payment terms accepted")
        await asyncio.sleep(0.5)

        place_btn = self.page.locator(Selectors.PAYMENT_PLACE_ORDER).first
        await place_btn.wait_for(state="visible", timeout=10000)
        for _ in range(10):
            if not await place_btn.is_disabled():
                break
            logger.debug("Place order button still disabled...")
            await asyncio.sleep(0.5)

        await self.delays.wait("before_pay_click")
        await place_btn.click()
        logger.debug("Order submitted, waiting for confirmation...")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3.0)

    # ── Helpers ──────────────────────────────────────────────────────────────
    async def _resolve_state_id(self) -> str:
        """Read the actual state IDs from the dropdown and match by province name."""
        result = await self.page.evaluate(f"""
            () => {{
                const sel = document.getElementById('field-id_state');
                if (!sel) return null;
                const opts = Array.from(sel.options)
                    .filter(o => o.value && o.value !== '0')
                    .map(o => ({{ value: o.value, text: o.text.trim() }}));

                // Try to match by province name keywords
                const city = '{self.customer.city}'.toLowerCase();
                const province = '{self.customer.province_code}'.toLowerCase();

                // Direct city match in option text
                const byCity = opts.find(o => o.text.toLowerCase().includes(city));
                if (byCity) return byCity.value;

                // Province code match
                const byProvince = opts.find(o => 
                    o.text.toLowerCase().includes(province) ||
                    o.value === province
                );
                if (byProvince) return byProvince.value;

                // Return first option as fallback
                return opts.length > 0 ? opts[0].value : null;
            }}
        """)
        return result or ""

    async def _fill_field(self, selector: str, value: str):
        try:
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=5000)
            await locator.click()
            await locator.fill(value)
        except Exception as e:
            logger.warning("Could not fill '%s': %s", selector, e)

    async def _js_fill(self, field_id: str, value: str):
        """Fill a field by ID using JS events — reliable for PrestaShop's React-like forms."""
        value_escaped = value.replace("'", "\\'")
        result = await self.page.evaluate(f"""
            () => {{
                const el = document.getElementById('{field_id}');
                if (!el) return 'not_found';
                el.focus();
                el.value = '{value_escaped}';
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                el.blur();
                return 'ok';
            }}
        """)
        logger.debug("JS fill #%s = '%s' → %s", field_id, value, result)

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
            if "confirmacion-pedido" in self.page.url or "order-confirmation" in self.page.url:
                break
            await asyncio.sleep(1.0)
        else:
            logger.warning("Did not reach confirmation page (url: %s)", self.page.url)
            return "unknown"

        logger.debug("Reached confirmation page: %s", self.page.url)
        match = re.search(r"id_order=(\d+)", self.page.url)
        return f"#{match.group(1)}" if match else "confirmed"
