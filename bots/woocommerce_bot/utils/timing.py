import asyncio
import random

DELAY_POINTS = [
    "product_page", "add_to_cart", "before_checkout",
    "first_name", "last_name", "email_after",
    "address1", "zip_code", "city", "address_done",
    "before_payment", "before_pay_click",
]

class OrderDelays:
    def __init__(self):
        total_budget = random.uniform(8.0, 16.0)
        weights = [random.random() for _ in DELAY_POINTS]
        weight_sum = sum(weights)
        self._delays = {
            point: (w / weight_sum) * total_budget
            for point, w in zip(DELAY_POINTS, weights)
        }

    async def wait(self, point: str):
        delay = self._delays.get(point, 0.0)
        if delay > 0.01:
            await asyncio.sleep(delay)

    def get(self, point: str) -> float:
        return self._delays.get(point, 0.0)

    @property
    def total(self) -> float:
        return sum(self._delays.values())
