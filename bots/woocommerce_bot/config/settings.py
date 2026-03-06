from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path

_GLOBAL_ENV = Path(__file__).parent.parent / ".env"


class BotSettings(BaseSettings):
    store_url: str = "https://woocomerce.mendepru.com/"
    store_email: Optional[str] = None
    store_password: Optional[str] = None
    num_orders: int = Field(default=10, ge=1, le=100)
    min_products_per_order: int = Field(default=1, ge=1)
    max_products_per_order: int = Field(default=1, ge=1)
    headless: bool = False
    slow_mo: int = 0
    browser_timeout: int = 60000
    delay_between_orders: float = 3.0
    max_retries_per_order: int = 3
    retry_delay: float = 5.0
    log_level: str = "INFO"
    log_file: Optional[str] = "bot_orders.log"
    screenshot_on_error: bool = True
    screenshots_dir: str = "screenshots"

    model_config = {"env_file": str(_GLOBAL_ENV), "env_prefix": "WOOCOMMERCE_BOT_"}
