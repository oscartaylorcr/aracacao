"""
Shopify → Softland daily sync entrypoint.

Usage:
  python main.py                 # normal run
  python main.py --verify        # test Shopify API + paths only
  python main.py --dry-run       # fetch orders, no Softland clicks (uses config DRY_RUN too)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from config import DRY_RUN, LOG_FILE, PROCESSED_ORDERS_FILE, SOFTLAND_EXE_PATH
from notifier import format_run_summary, send_summary
from shopify_client import fetch_orders_for_sync, test_connection
from softland_bot import initialize_session, run_order_through_softland

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_processed_ids() -> set[int]:
    if not PROCESSED_ORDERS_FILE.is_file():
        return set()
    try:
        with open(PROCESSED_ORDERS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        ids = data.get("order_ids") or []
        return {int(x) for x in ids}
    except Exception:
        logger.exception("Could not read processed orders file; starting fresh.")
        return set()


def save_processed_ids(ids: set[int]) -> None:
    PROCESSED_ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"order_ids": sorted(ids)}, f, indent=2)


def verify_only() -> int:
    """Quick preflight for meeting: Shopify + optional Softland exe path."""
    setup_logging()
    logging.info("Verify: testing Shopify API...")
    shop = test_connection()
    name = shop.get("shop", {}).get("name", "?")
    logging.info("Shopify OK: shop name = %s", name)

    exe = Path(SOFTLAND_EXE_PATH)
    if exe.is_file():
        logging.info("Softland exe found: %s", exe)
    else:
        logging.warning(
            "Softland exe not found at SOFTLAND_EXE_PATH=%s (OK if Softland is already open manually).",
            exe,
        )
    return 0


def run_sync(dry_run: bool) -> int:
    setup_logging()
    dry = dry_run or DRY_RUN
    results: list[dict] = []

    try:
        orders = fetch_orders_for_sync()
    except Exception as e:
        logger.exception("Failed to fetch Shopify orders: %s", e)
        send_summary(
            "Shopify → Softland FAILED",
            f"Fetch error: {e}",
        )
        return 1

    processed = load_processed_ids()
    pending = [o for o in orders if int(o["id"]) not in processed]

    if not pending:
        logger.info("No new orders to process (all fetched orders already in processed_orders.json).")
        plain, html = format_run_summary(
            [{"order_id": None, "order_name": "-", "status": "noop", "error": "no new orders"}]
        )
        send_summary("Shopify → Softland: no new orders", plain, html)
        return 0

    logger.info("Processing %d order(s) (dry_run=%s)", len(pending), dry)

    if not dry:
        try:
            initialize_session()
        except Exception as e:
            logger.exception("Softland session init failed: %s", e)
            send_summary("Shopify → Softland FAILED", f"Softland init: {e}")
            return 1

    new_ids: list[int] = []
    for order in pending:
        oid = int(order["id"])
        name = order.get("name") or str(oid)
        try:
            if dry:
                logger.info("[DRY RUN] Would create invoice for %s — %s line(s)", name, len(order.get("line_items") or []))
                for li in order.get("line_items") or []:
                    logger.info("  line: sku=%s qty=%s", li.get("sku"), li.get("quantity"))
                results.append({"order_id": oid, "order_name": name, "status": "dry_run", "error": ""})
            else:
                run_order_through_softland(order)
                results.append({"order_id": oid, "order_name": name, "status": "ok", "error": ""})
                new_ids.append(oid)
        except Exception as e:
            logger.exception("Order %s failed: %s", name, e)
            results.append({"order_id": oid, "order_name": name, "status": "error", "error": str(e)})

    if new_ids:
        processed.update(new_ids)
        save_processed_ids(processed)

    plain, html = format_run_summary(results)
    send_summary("Shopify → Softland run complete", plain, html)
    failed = sum(1 for r in results if r.get("status") == "error")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shopify to Softland sync")
    parser.add_argument("--verify", action="store_true", help="Test Shopify + exe path only")
    parser.add_argument("--dry-run", action="store_true", help="No Softland automation")
    args = parser.parse_args()

    if args.verify:
        return verify_only()
    return run_sync(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
