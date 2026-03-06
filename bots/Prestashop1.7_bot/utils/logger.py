import logging
import sys

from rich.console import Console

from config.settings import BotSettings

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True)


class BotLogHandler(logging.Handler):
    """Outputs [LOG] / [WARN] / [ERROR] prefix with rich markup support."""

    def emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
            if record.levelno >= logging.ERROR:
                console.print(f"[bold red][ERROR][/bold red] {msg}", markup=True)
            elif record.levelno >= logging.WARNING:
                console.print(f"[yellow][WARN][/yellow]  {msg}", markup=True)
            else:
                console.print(f"[dim][LOG][/dim]   {msg}", markup=True)
        except Exception:
            self.handleError(record)


def setup_logger(settings: BotSettings) -> logging.Logger:
    for name in ("prestashop_bot", "ps17_bot"):
        lg = logging.getLogger(name)
        lg.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        lg.propagate = False

        if not lg.handlers:
            handler = BotLogHandler()
            handler.setLevel(logging.DEBUG)
            lg.addHandler(handler)

            if settings.log_file:
                file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s | %(levelname)-8s | %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                lg.addHandler(file_handler)

    return logging.getLogger("prestashop_bot")
