"""
Shopify Admin REST API: fetch orders for sync.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from config import (
    SHOPIFY_ACCESS_TOKEN,
    SHOPIFY_API_VERSION,
    SHOPIFY_FINANCIAL_STATUS,
    SHOPIFY_LOOKBACK_HOURS,
    SHOPIFY_MAX_ORDERS,
    SHOPIFY_SHOP,
)

logger = logging.getLogger(__name__)


def _normalize_shop_domain(shop: str) -> str:
    s = shop.strip().lower()
    if not s.endswith(".myshopify.com"):
        s = f"{s}.myshopify.com"
    return s


def _base_url() -> str:
    domain = _normalize_shop_domain(SHOPIFY_SHOP)
    return f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}"


def _headers() -> dict[str, str]:
    if not SHOPIFY_ACCESS_TOKEN:
        raise ValueError("SHOPIFY_ACCESS_TOKEN is not set in config or environment.")
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def test_connection() -> dict[str, Any]:
    """Lightweight check: GET shop.json."""
    url = f"{_base_url()}/shop.json"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_orders_for_sync() -> list[dict[str, Any]]:
    """
    Fetch orders created in the lookback window, filtered by financial status.
    Returns list of normalized order dicts for the bot.
    """
    created_at_min = datetime.now(timezone.utc) - timedelta(hours=SHOPIFY_LOOKBACK_HOURS)
    min_iso = created_at_min.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    params: dict[str, Any] = {
        "status": "any",
        "created_at_min": min_iso,
        "limit": min(250, SHOPIFY_MAX_ORDERS),
    }
    if SHOPIFY_FINANCIAL_STATUS:
        params["financial_status"] = SHOPIFY_FINANCIAL_STATUS

    url = f"{_base_url()}/orders.json"
    logger.info("GET %s with created_at_min=%s", url, min_iso)

    r = requests.get(url, headers=_headers(), params=params, timeout=60)
    if r.status_code == 400 and "financial_status" in params:
        logger.warning("Retrying orders fetch without financial_status filter")
        del params["financial_status"]
        r = requests.get(url, headers=_headers(), params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    orders = data.get("orders") or []

    # Client-side cap and stable order (oldest first)
    if len(orders) > SHOPIFY_MAX_ORDERS:
        orders = orders[: SHOPIFY_MAX_ORDERS]

    try:
        orders.sort(key=lambda o: o.get("created_at") or "")
    except Exception:
        pass

    normalized = [_normalize_order(o) for o in orders]
    return normalized


def _normalize_order(raw: dict[str, Any]) -> dict[str, Any]:
    """Map Shopify order to a stable structure for Softland."""
    order_id = raw.get("id")
    name = raw.get("name") or str(order_id)
    customer = raw.get("customer") or {}
    billing = raw.get("billing_address") or {}
    shipping = raw.get("shipping_address") or billing

    line_items: list[dict[str, Any]] = []
    for li in raw.get("line_items") or []:
        sku = (li.get("sku") or "").strip()
        if not sku:
            sku = f"NO-SKU-{li.get('id')}"
        line_items.append(
            {
                "sku": sku,
                "title": li.get("title") or "",
                "quantity": int(li.get("quantity") or 0),
                "price": str(li.get("price") or "0"),
            }
        )

    return {
        "id": order_id,
        "name": name,
        "email": raw.get("email") or customer.get("email") or "",
        "currency": raw.get("currency") or "USD",
        "total_price": raw.get("total_price") or "0",
        "customer_name": _customer_display_name(customer, billing),
        "billing": {
            "name": billing.get("name") or "",
            "address1": billing.get("address1") or "",
            "city": billing.get("city") or "",
            "zip": billing.get("zip") or "",
        },
        "shipping": {
            "name": shipping.get("name") or "",
            "address1": shipping.get("address1") or "",
            "city": shipping.get("city") or "",
            "zip": shipping.get("zip") or "",
        },
        "line_items": line_items,
        "raw": raw,
    }


def _customer_display_name(customer: dict, billing: dict) -> str:
    if billing.get("name"):
        return billing["name"]
    first = customer.get("first_name") or ""
    last = customer.get("last_name") or ""
    return f"{first} {last}".strip() or "Customer"

