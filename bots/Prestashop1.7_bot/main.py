import asyncio
import argparse
import random
import sys
import time

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
from utils.logger import setup_logger
from utils.timing import OrderDelays

console = Console(force_terminal=True)


def parse_args():
    parser = argparse.ArgumentParser(description="PrestaShop 1.7 Test Order Bot")
    parser.add_argument("--orders",   type=int,   help="Number of orders")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--slow-mo",  type=int,   help="Slow motion ms")
    parser.add_argument("--delay",    type=float, help="Delay between orders (s)")
    parser.add_argument("--province", type=str,   default=None, help="Provincia para las direcciones (ej: Valencia, Madrid)")
    return parser.parse_args()


async def process_single_order(
    browser_mgr, settings, customer_gen, product_urls, order_index, total_orders, logger
) -> OrderResult:
    start_time = time.time()
    customer = customer_gen.generate()

    logger.info(
        "[yellow][[Order %d/%d]] EN EJECUCION[/yellow]",
        order_index, total_orders,
    )
    logger.info(
        "Cliente: [cyan]%s %s[/cyan] | [dim]%s[/dim]",
        customer.first_name, customer.last_name, customer.email,
    )

    context, page = await browser_mgr.new_context()
    result = OrderResult(order_index=order_index, success=False, customer_email=customer.email)

    try:
        delays = OrderDelays()

        navigator = StoreNavigator(page, settings, delays)

        num = random.randint(settings.min_products_per_order, settings.max_products_per_order)
        selected = random.sample(product_urls, min(num, len(product_urls)))
        logger.info("Producto seleccionado (%d)", len(selected))

        cart_mgr = CartManager(page, settings, delays)
        added = 0
        for url in selected:
            if await navigator.navigate_to_product(url):
                logger.info("Producto encontrado [green]✓[/green]")
                await navigator.select_random_variant()
                if await cart_mgr.add_to_cart():
                    added += 1
                    logger.info("Producto añadido al carrito [green]✓[/green]")

        if added == 0:
            raise Exception("Could not add any products to cart")

        if not await cart_mgr.proceed_to_checkout():
            raise Exception("Failed to proceed to checkout")

        checkout = CheckoutHandler(page, settings, customer, delays)
        result = await checkout.complete_checkout(order_index, total_orders)
        result.customer_email = customer.email

    except Exception as e:
        result.error_message = str(e)
        logger.error("[[Order %d/%d]] FALLIDO: %s", order_index, total_orders, e)

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

    if args.orders:   settings.num_orders = args.orders
    if args.headless: settings.headless = True
    if args.slow_mo:  settings.slow_mo = args.slow_mo
    if args.delay is not None: settings.delay_between_orders = args.delay
    if args.province: settings.province = args.province

    logger = setup_logger(settings)
    customer_gen = CustomerGenerator(province=settings.province)
    browser_mgr = BrowserManager(settings)
    results: list[OrderResult] = []

    console.rule(f"[bold green]{settings.bot_name}[/bold green]")
    console.print(f"[BOT] Store:    [cyan]{settings.store_url}[/cyan]")
    console.print(f"[BOT] Orders:   {settings.num_orders}")
    console.print(f"[BOT] Headless: {settings.headless}")
    console.print()

    try:
        await browser_mgr.launch()

        # Scrape products (public page)
        context, page = await browser_mgr.new_context()
        navigator = StoreNavigator(page, settings)
        product_urls = await navigator.get_product_urls()
        await context.close()

        if not product_urls:
            console.print("[bold red]No products found! Check the store URL.[/bold red]")
            return

        console.print()

        for i in range(1, settings.num_orders + 1):
            result = await process_single_order(
                browser_mgr, settings, customer_gen, product_urls, i, settings.num_orders, logger
            )
            results.append(result)

            if i < settings.num_orders:
                delay = random.uniform(
                    settings.delay_between_orders * 0.5,
                    settings.delay_between_orders * 1.5,
                )
                await asyncio.sleep(delay)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {e}[/bold red]")
        logger.exception("Fatal error")
    finally:
        await browser_mgr.close()

    _print_summary(results)


def _print_summary(results: list[OrderResult]):
    if not results:
        return
    console.print()
    console.rule("[bold blue]ORDER BOT SUMMARY[/bold blue]")
    successful = [r for r in results if r.success]
    total_time = sum(r.duration_seconds for r in results)

    console.print(f"  Total Attempted:  {len(results)}")
    console.print(f"  [green]Successful:[/green]       {len(successful)}")
    console.print(f"  [red]Failed:[/red]           {len(results) - len(successful)}")
    console.print(f"  Success Rate:     {len(successful)/len(results)*100:.1f}%\n")

    table = Table(title="Order Details")
    table.add_column("#",         style="dim", width=4)
    table.add_column("Status",    width=10)
    table.add_column("Customer",  width=25)
    table.add_column("Order Ref", width=10)
    table.add_column("Time",      width=8, justify="right")
    table.add_column("Error",     width=35)

    for r in results:
        status   = "[green]SUCCESS[/green]" if r.success else "[red]FAILED[/red]"
        customer = (r.customer_email or "---").split("@")[0]
        table.add_row(str(r.order_index), status, customer,
                      r.order_number or "---", f"{r.duration_seconds:.1f}s",
                      (r.error_message or "")[:35])

    console.print(table)
    if total_time:
        console.print(f"\n  Total Time:    {total_time:.1f}s")
        console.print(f"  Avg per Order: {total_time/len(results):.1f}s")
    console.rule()


if __name__ == "__main__":
    asyncio.run(run_bot())
