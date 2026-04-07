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

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WooCommerce Test Order Bot")
    parser.add_argument("--orders",   type=int,   help="Número de pedidos a generar")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo headless")
    parser.add_argument("--slow-mo",  type=int,   help="Slow motion delay en ms")
    parser.add_argument("--delay",    type=float, default=None, help="Delay entre pedidos (segundos)")
    parser.add_argument("--province", type=str,   default=None, help="Provincia para las direcciones (ej: Valencia, MD, B)")
    return parser.parse_args()

async def process_single_order(
    browser_mgr, settings, customer_gen, product_urls, order_index, total_orders, logger
) -> OrderResult:
    start_time = time.time()
    customer = customer_gen.generate()
    logger.order_start(order_index, total_orders)
    logger.cliente(f"{customer.first_name} {customer.last_name}", customer.email)
    context, page = await browser_mgr.new_context()
    result = OrderResult(order_index=order_index, success=False, customer_email=customer.email)
    try:
        delays = OrderDelays()
        navigator = StoreNavigator(page, settings, delays)
        num_products = random.randint(settings.min_products_per_order, settings.max_products_per_order)
        selected = random.sample(product_urls, min(num_products, len(product_urls)))
        logger.info("Producto seleccionado (%d)", len(selected))
        cart_mgr = CartManager(page, settings, delays)
        added = 0
        for url in selected:
            if await navigator.navigate_to_product(url):
                await navigator.select_random_variant()
                if await cart_mgr.add_to_cart():
                    added += 1
        if added == 0:
            raise Exception("No se pudo añadir ningún producto al carrito")
        if not await cart_mgr.proceed_to_checkout():
            raise Exception("Error al proceder al pago")
        checkout = CheckoutHandler(page, settings, customer, delays)
        result = await checkout.complete_checkout(order_index, total_orders)
        result.customer_email = customer.email
    except Exception as e:
        result.error_message = str(e)
        logger.error("[Order %d/%d] Error: %s", order_index, total_orders, e)
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
    if args.orders: settings.num_orders = args.orders
    if args.headless: settings.headless = True
    if args.slow_mo: settings.slow_mo = args.slow_mo
    if args.delay is not None: settings.delay_between_orders = args.delay
    if args.province: settings.province = args.province

    logger = setup_logger(settings)
    customer_gen = CustomerGenerator(province=settings.province)
    browser_mgr = BrowserManager(settings)
    results = []

    logger.banner("BOT WOOCOMMERCE")
    logger.bot("Store", settings.store_url)
    logger.bot("Orders", settings.num_orders)
    logger.bot("Headless", settings.headless)
    console.print()

    try:
        await browser_mgr.launch()
        context, page = await browser_mgr.new_context()
        navigator = StoreNavigator(page, settings)
        product_urls = await navigator.get_product_urls()
        await context.close()

        if not product_urls:
            logger.error("No se encontraron productos. Revisa COLLECTION_ALL en selectors.py")
            return

        logger.info("Productos encontrados: %d", len(product_urls))
        console.print()

        for i in range(1, settings.num_orders + 1):
            result = await process_single_order(
                browser_mgr, settings, customer_gen, product_urls, i, settings.num_orders, logger
            )
            results.append(result)
            if i < settings.num_orders:
                delay = random.uniform(settings.delay_between_orders * 0.5, settings.delay_between_orders * 1.5)
                await asyncio.sleep(delay)

    except KeyboardInterrupt:
        console.print("\n[yellow]Bot interrumpido por el usuario[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error fatal: {e}[/bold red]")
        logger.exception("Error fatal")
    finally:
        await browser_mgr.close()

    _print_summary(results)

def _print_summary(results):
    if not results:
        console.print("[yellow]No orders were processed[/yellow]")
        return
    console.print()
    console.rule("[bold blue]ORDER BOT SUMMARY[/bold blue]")
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    total_time = sum(r.duration_seconds for r in results)
    console.print(f"  Total:      {len(results)}")
    console.print(f"  [green]Successful:[/green] {len(successful)}")
    console.print(f"  [red]Failed:[/red]     {len(failed)}")
    if results:
        console.print(f"  Success:    {len(successful)/len(results)*100:.1f}%")
    console.print()
    table = Table(title="Order Details")
    table.add_column("#", style="dim", width=4)
    table.add_column("Status", width=10)
    table.add_column("Customer", width=25)
    table.add_column("Order Ref", width=10)
    table.add_column("Time", width=8, justify="right")
    table.add_column("Error", width=35)
    for r in results:
        status = "[green]SUCCESS[/green]" if r.success else "[red]FAILED[/red]"
        customer = (r.customer_email or "---").split("@")[0]
        table.add_row(str(r.order_index), status, customer, r.order_number or "---",
                      f"{r.duration_seconds:.1f}s", (r.error_message or "")[:35])
    console.print(table)
    if total_time > 0:
        console.print(f"\n  Total Time:    {total_time:.1f}s")
        console.print(f"  Avg per Order: {total_time/len(results):.1f}s")
    console.rule()

if __name__ == "__main__":
    asyncio.run(run_bot())
