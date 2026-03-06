import logging
import sys

from rich.console import Console
from rich.markup import escape

from config.settings import BotSettings

# Force UTF-8 output on Windows to avoid encoding errors with Rich
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True)


def log_info(msg: str):
    """Print a [LOG] prefixed message with Rich markup support."""
    console.print(f"[dim]\\[LOG][/dim] {msg}", markup=True)


def log_order_running(order_index: int, total: int):
    """Print full yellow line for order start."""
    console.print(f"[yellow]\\[LOG] \\[Order {order_index}/{total}] EN EJECUCION[/yellow]", markup=True)


def log_order_done(order_index: int, total: int, ref: str):
    """Print full green line for order completion."""
    console.print(f"[green]\\[LOG] \\[Order {order_index}/{total}] COMPLETADO - Ref: {ref} ✓[/green]", markup=True)


class _BotLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = escape(record.getMessage())
            if record.levelno >= logging.ERROR:
                console.print(f"[bold red]\\[ERROR][/bold red] {msg}", markup=True)
            elif record.levelno >= logging.WARNING:
                console.print(f"[bold yellow]\\[WARNING][/bold yellow] {msg}", markup=True)
            else:
                console.print(f"[dim]\\[LOG][/dim] {msg}", markup=True)
        except Exception:
            self.handleError(record)


def setup_logger(settings: BotSettings) -> logging.Logger:
    logger = logging.getLogger("shopify_bot")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = _BotLogHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        if settings.log_file:
            file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            logger.addHandler(file_handler)

    return logger
