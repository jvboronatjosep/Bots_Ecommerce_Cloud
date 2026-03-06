import logging
import sys

from rich.logging import RichHandler
from rich.console import Console

from config.settings import BotSettings

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True)


def setup_logger(settings: BotSettings) -> logging.Logger:
    logger = logging.getLogger("prestashop_bot")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        if settings.log_file:
            file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(file_handler)

    return logger
