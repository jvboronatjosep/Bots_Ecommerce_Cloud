import asyncio
import argparse
import random
import sys
import time

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table

from config.settings import BotSettings
from core.browser import BrowserManager
from core.store_navigator import StoreNavigator
from core.cart_manager import CartManager
from core.checkout_handler import CheckoutHandler, OrderResult
from data.fake_customer import CustomerGenerator
from utils.logger import setup_logger, log_info, log_order_running, log_order_done, console
from utils.timing import OrderDelays


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shopify Test Order Bot")
    parser.add_argument("--orders", type=int, help="Number of orders to generate")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--products-per-order", type=int, help="Max products per order")
    parser.add_argument("--slow-mo", type=int, help="Slow motion delay in ms")
    parser.add_argument("--delay", type=float, default=None, help="Delay between orders in seconds (default: 3)")
    return parser.parse_args()


async def process_single_order(
    browser_mgr: BrowserManager,
    settings: BotSettings,
    customer_gen: CustomerGenerator,
    product_urls: list[str],
    order_index: int,
    logger,
) -> OrderResult:
    start_time = time.time()
    total = settings.num_orders
    customer = customer_gen.generate()

    log_order_running(order_index, total)
    log_info(f"Cliente: [cyan]{customer.first_name} {customer.last_name}[/cyan] | [dim]{customer.email}[/dim]")

    context, page = await browser_mgr.new_context()
    result = OrderResult(order_index=order_index, success=False, customer_email=customer.email)

    try:
        delays = OrderDelays()

        navigator = StoreNavigator(page, settings, delays)

        num_products = random.randint(settings.min_products_per_order, settings.max_products_per_order)
        selected = random.sample(product_urls, min(num_products, len(product_urls)))
        log_info(f"Producto seleccionado ({len(selected)})")

        cart_mgr = CartManager(page, settings, delays)
        added = 0
        for i, url in enumerate(selected):
            if await navigator.navigate_to_product(url):
                await navigator.select_random_variant()
                if await cart_mgr.add_to_cart():
                    added += 1
                    if i < len(selected) - 1:
                        await cart_mgr.close_cart_drawer()

        if added == 0:
            raise Exception("Could not add any products to cart")

        if not await cart_mgr.proceed_to_checkout():
            raise Exception("Failed to proceed to checkout")

        checkout = CheckoutHandler(page, settings, customer, delays)
        result = await checkout.complete_checkout(order_index)
        result.customer_email = customer.email

        if result.success:
            log_order_done(order_index, total, result.order_number)

    except Exception as e:
        result.error_message = str(e)
        logger.error("[Order %d/%d] FALLIDO: %s", order_index, total, e)

        try:
            screenshot_path = await browser_mgr.take_screenshot(page, f"error_order_{order_index}")
            result.screenshot_path = screenshot_path
        except Exception:
            pass

    finally:
        result.duration_seconds = time.time() - start_time
        try:
            await page.close()
        except Exception:
            pass
        await context.close()

    return result


async def run_bot():
    args = parse_args()
    settings = BotSettings()

    if args.orders:
        settings.num_orders = args.orders
    if args.headless:
        settings.headless = True
    if args.products_per_order:
        settings.max_products_per_order = args.products_per_order
    if args.slow_mo:
        settings.slow_mo = args.slow_mo
    if args.delay is not None:
        settings.delay_between_orders = args.delay

    logger = setup_logger(settings)
    customer_gen = CustomerGenerator()
    browser_mgr = BrowserManager(settings)
    results: list[OrderResult] = []

    console.rule("[bold green]BOT COMPRAS SHOPIFY[/bold green]", style="green")
    console.print(f"[dim]\\[BOT][/dim] Store:    [cyan]{settings.store_url}[/cyan]", markup=True)
    console.print(f"[dim]\\[BOT][/dim] Orders:   {settings.num_orders}", markup=True)
    console.print(f"[dim]\\[BOT][/dim] Headless: {settings.headless}", markup=True)
    console.print()

    try:
        await browser_mgr.launch()

        context, page = await browser_mgr.new_context()
        navigator = StoreNavigator(page, settings)
        await navigator.bypass_password_page()
        await browser_mgr.store_cookies(context)
        product_urls = await navigator.get_product_urls()
        await context.close()

        if not product_urls:
            console.print("[bold red]No products found in the store! Exiting.[/bold red]")
            return

        log_info(f"Productos encontrados: [green]{len(product_urls)}[/green]")
        console.print()

        for i in range(1, settings.num_orders + 1):
            result = await process_single_order(
                browser_mgr, settings, customer_gen, product_urls, i, logger,
            )
            results.append(result)

            if i < settings.num_orders:
                delay = random.uniform(
                    settings.delay_between_orders * 0.5,
                    settings.delay_between_orders * 1.5,
                )
                await asyncio.sleep(delay)

    except KeyboardInterrupt:
        console.print("\n[yellow]Bot interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {e}[/bold red]")
        logger.exception("Fatal error")
    finally:
        await browser_mgr.close()

    print_summary(results)


def print_summary(results: list[OrderResult]):
    if not results:
        console.print("[yellow]No orders were processed[/yellow]")
        return

    console.print()
    console.rule("[bold green]RESUMEN[/bold green]")

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    total_time = sum(r.duration_seconds for r in results)

    console.print(f"  Total:             {len(results)}")
    console.print(f"  [green]Completados:[/green]       {len(successful)}")
    console.print(f"  [red]Fallidos:[/red]          {len(failed)}")

    if results:
        rate = len(successful) / len(results) * 100
        console.print(f"  Tasa de exito:     {rate:.1f}%")

    console.print()

    table = Table(title="Detalle de Ordenes")
    table.add_column("#", style="dim", width=4)
    table.add_column("Estado", width=12)
    table.add_column("Referencia", width=20)
    table.add_column("Email", width=40)
    table.add_column("Tiempo", width=8, justify="right")
    table.add_column("Error", width=30)

    for r in results:
        status = "[green]COMPLETADO[/green]" if r.success else "[red]FALLIDO[/red]"
        order_num = r.order_number or "---"
        email = r.customer_email or "---"
        duration = f"{r.duration_seconds:.1f}s"
        error = (r.error_message or "")[:30]
        table.add_row(str(r.order_index), status, order_num, email, duration, error)

    console.print(table)

    if total_time > 0:
        avg_time = total_time / len(results)
        console.print(f"\n  Tiempo total:   {total_time:.1f}s")
        console.print(f"  Media por orden: {avg_time:.1f}s")

    console.rule()


if __name__ == "__main__":
    asyncio.run(run_bot())
