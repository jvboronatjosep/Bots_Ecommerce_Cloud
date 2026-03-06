import logging
import re
import sys
from rich.console import Console
from config.settings import BotSettings

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True, highlight=False)

_instance: "BotLogger | None" = None


class BotLogger:
    """Rich-formatted console logger with semantic helper methods."""

    def __init__(self, file_logger: logging.Logger | None = None):
        self._file = file_logger

    # ── Layout helpers ───────────────────────────────────────────────────────

    def banner(self, title: str) -> None:
        """Print a green banner: ─── TITLE ───"""
        console.rule(f"[bold green]{title}[/]", style="green")

    def bot(self, key: str, value) -> None:
        """Print a [BOT] config line with value in cyan, keys aligned."""
        console.print(f"\\[BOT] {key:<9}[cyan]{value}[/]")

    # ── Semantic order helpers ───────────────────────────────────────────────

    def order_start(self, current: int, total: int) -> None:
        """[LOG] [Order X/Y] EN EJECUCION  ← full line yellow"""
        msg = f"[Order {current}/{total}] EN EJECUCION"
        console.print(f"[yellow]\\[LOG] {msg}[/]")
        self._log_file("info", msg)

    def order_done(self, current: int, total: int, ref: str) -> None:
        """[LOG] [Order X/Y] COMPLETADO - Ref: #xxx ✓  ← full line green"""
        msg = f"[Order {current}/{total}] COMPLETADO - Ref: {ref} ✓"
        console.print(f"[green]\\[LOG] {msg}[/]")
        self._log_file("info", msg)

    def cliente(self, name: str, email: str) -> None:
        """[LOG] Cliente: NAME (cyan) | email (dim)"""
        console.print(f"\\[LOG] Cliente: [cyan]{name}[/] | [dim]{email}[/]")
        self._log_file("info", f"Cliente: {name} | {email}")

    def paso(self, current: int, total: int, description: str) -> None:
        """[LOG] Paso N/T: Description  ← N in cyan"""
        console.print(f"\\[LOG] Paso [cyan]{current}[/]/{total}: {description}")
        self._log_file("info", f"Paso {current}/{total}: {description}")

    # ── Standard logging interface ───────────────────────────────────────────

    def info(self, msg: str, *args) -> None:
        text = msg % args if args else msg
        console.print(f"\\[LOG] {self._style(text)}")
        self._log_file("info", text)

    def error(self, msg: str, *args) -> None:
        text = msg % args if args else msg
        console.print(f"[bold red]\\[ERROR][/] [red]{text}[/]")
        self._log_file("error", text)

    def warning(self, msg: str, *args) -> None:
        text = msg % args if args else msg
        console.print(f"[bold yellow]\\[WARNING][/] [yellow]{text}[/]")
        self._log_file("warning", text)

    def debug(self, msg: str, *args) -> None:
        text = msg % args if args else msg
        self._log_file("debug", text)

    def exception(self, msg: str, *args) -> None:
        text = msg % args if args else msg
        console.print(f"[bold red]\\[ERROR][/] [red]{text}[/]")
        console.print_exception(show_locals=False)
        self._log_file("error", text)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _style(self, text: str) -> str:
        """Apply context-aware coloring to INFO messages."""
        # Full line yellow — order in progress
        if re.search(r'\[Order \d+', text) and re.search(r'EN EJECUCION|Starting', text, re.I):
            return f"[yellow]{text}[/]"
        # Full line green — order completed
        if re.search(r'\[Order \d+', text) and re.search(r'COMPLETADO|Completed', text, re.I):
            return f"[green]{text}[/]"
        # ✓ in green
        text = text.replace("✓", "[green]✓[/]")
        # Numbers after ": " in green  (e.g. "Productos encontrados: 12")
        text = re.sub(r"(:\s*)(\d+)", r"\1[green]\2[/]", text)
        return text

    def _log_file(self, level: str, text: str) -> None:
        if self._file:
            getattr(self._file, level)(text)


def get_logger() -> BotLogger:
    global _instance
    if _instance is None:
        _instance = BotLogger()
    return _instance


def setup_logger(settings: BotSettings) -> BotLogger:
    global _instance
    file_logger = None
    if settings.log_file:
        file_logger = logging.getLogger("woocommerce_bot_file")
        file_logger.setLevel(logging.DEBUG)
        file_logger.propagate = False
        if not file_logger.handlers:
            fh = logging.FileHandler(settings.log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            file_logger.addHandler(fh)
    if _instance is None:
        _instance = BotLogger(file_logger)
    else:
        _instance._file = file_logger
    return _instance
