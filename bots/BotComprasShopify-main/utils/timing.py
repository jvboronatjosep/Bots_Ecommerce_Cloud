import asyncio
import random

MAX_TOTAL_DELAY = 10.0  # seconds max across all delays in one order

# All delay points in the order flow
DELAY_POINTS = [
    "product_page",        # after loading product page
    "add_to_cart",         # after clicking add to cart
    "before_checkout",     # after clicking checkout button
    "email_before",        # before typing email
    "email_after",         # after typing email
    "country_select",      # after selecting country
    "first_name",          # after filling first name
    "last_name",           # after filling last name
    "address1",            # after filling address
    "address2",            # after filling address2
    "city",                # after filling city
    "province",            # after selecting province
    "zip_code",            # after filling zip
    "address_done",        # after all address fields
    "before_payment",      # before starting payment
    "card_number",         # after filling card number
    "card_expiry",         # after filling expiry
    "card_cvv",            # after filling cvv
    "card_name",           # after filling card name
    "before_pay_click",    # before clicking pay now
]


class OrderDelays:
    """Generates a unique random delay profile for each order.

    Distributes a random total budget (up to MAX_TOTAL_DELAY) across
    all delay points, so each order has a different timing pattern.
    """

    def __init__(self):
        # Pick a random total budget between 10s and 20s
        total_budget = random.uniform(10.0, 20.0)

        # Generate random weights for each point
        weights = [random.random() for _ in DELAY_POINTS]
        weight_sum = sum(weights)

        # Distribute budget proportionally
        self._delays = {}
        for point, w in zip(DELAY_POINTS, weights):
            self._delays[point] = (w / weight_sum) * total_budget

    async def wait(self, point: str):
        """Wait the pre-calculated delay for this point."""
        delay = self._delays.get(point, 0.0)
        if delay > 0.01:
            await asyncio.sleep(delay)

    def get(self, point: str) -> float:
        """Get the delay value for a point (for logging)."""
        return self._delays.get(point, 0.0)

    @property
    def total(self) -> float:
        return sum(self._delays.values())
