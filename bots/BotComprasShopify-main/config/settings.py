from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path

_GLOBAL_ENV = Path(__file__).parent.parent.parent.parent.parent / ".env"


class BotSettings(BaseSettings):
    # Store
    store_url: str = "https://store-sendingbay.myshopify.com/"
    store_password: str = "meadai"

    # Orders
    num_orders: int = Field(default=10, ge=1, le=100)
    min_products_per_order: int = Field(default=1, ge=1)
    max_products_per_order: int = Field(default=1, ge=1)
    min_quantity_per_product: int = Field(default=1, ge=1)
    max_quantity_per_product: int = Field(default=1, ge=1)

    # Payment (Bogus Gateway defaults)
    payment_card_number: str = "1"
    payment_card_name: str = "Bogus Gateway"
    payment_card_expiry: str = "12/28"
    payment_card_cvv: str = "123"

    # Browser
    headless: bool = False
    slow_mo: int = 0
    browser_timeout: int = 60000

    # Human-like timing
    min_action_delay: float = 0.5
    max_action_delay: float = 2.0
    min_typing_delay: int = 50
    max_typing_delay: int = 150
    page_load_wait: float = 3.0
    delay_between_orders: float = 3.0

    # Retry
    max_retries_per_order: int = 3
    retry_delay: float = 5.0

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "bot_orders.log"
    screenshot_on_error: bool = True
    screenshots_dir: str = "screenshots"

    model_config = {"env_file": str(_GLOBAL_ENV), "env_prefix": "SHOPIFY_BOT_"}
