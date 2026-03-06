import logging

from playwright.async_api import Page

from config.settings import BotSettings
from utils.selectors import Selectors
from utils.timing import OrderDelays

logger = logging.getLogger("shopify_bot")


class PaymentHandler:
    def __init__(self, page: Page, settings: BotSettings, delays: OrderDelays):
        self.page = page
        self.settings = settings
        self.delays = delays

    async def fill_payment_fields(self):

        # Each iframe contains ALL 8 inputs (for browser autofill).
        # We must target the correct input by name/id inside each iframe.

        await self._fill_iframe_field(
            Selectors.CARD_NUMBER_IFRAME, "input#number",
            self.settings.payment_card_number, "card number",
        )
        await self.delays.wait("card_number")

        await self._fill_iframe_field(
            Selectors.CARD_EXPIRY_IFRAME, "input#expiry",
            self.settings.payment_card_expiry, "expiry date",
        )
        await self.delays.wait("card_expiry")

        await self._fill_iframe_field(
            Selectors.CARD_CVV_IFRAME, "input#verification_value",
            self.settings.payment_card_cvv, "CVV",
        )
        await self.delays.wait("card_cvv")

        await self._fill_iframe_field(
            Selectors.CARD_NAME_IFRAME, "input#name",
            self.settings.payment_card_name, "cardholder name",
        )
        await self.delays.wait("card_name")


    async def _fill_iframe_field(
        self, iframe_selector: str, input_selector: str, value: str, field_name: str
    ):
        try:
            iframe = self.page.locator(iframe_selector).first
            await iframe.wait_for(state="visible", timeout=10000)

            frame = self.page.frame_locator(iframe_selector).first
            input_field = frame.locator(input_selector)

            await input_field.click()
            await input_field.fill(value)
            logger.debug("Filled %s", field_name)
        except Exception as e:
            logger.warning("Could not fill %s: %s", field_name, e)
