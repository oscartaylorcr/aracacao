"""
Softland ERP UI automation using calibrated screen coordinates.
Requires coords_captured.json from calibrate.py on this machine.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import pyautogui
import pygetwindow as gw

from config import (
    COORDS_FILE,
    DELAYS,
    PYAUTOGUI_FAILSAFE,
    SKU_MAP,
    SOFTLAND_EXE_PATH,
    SOFTLAND_PASSWORD,
    SOFTLAND_USER,
    SOFTLAND_WINDOW_TITLE_SUBSTRING,
)

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE
pyautogui.PAUSE = DELAYS["between_clicks"]


def load_coords() -> dict[str, list[int]]:
    if not COORDS_FILE.is_file():
        raise FileNotFoundError(
            f"Missing {COORDS_FILE}. Run: python calibrate.py"
        )
    with open(COORDS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("coords file must be a JSON object of name -> [x, y]")
    return {k: v for k, v in data.items() if isinstance(v, list) and len(v) >= 2}


def _click(coords: dict[str, list[int]], key: str) -> None:
    if key not in coords:
        raise KeyError(f"Missing coordinate key '{key}' in {COORDS_FILE}")
    x, y = int(coords[key][0]), int(coords[key][1])
    logger.debug("click %s at (%s, %s)", key, x, y)
    pyautogui.click(x, y)
    time.sleep(DELAYS["between_clicks"])


def _type_text(text: str) -> None:
    # Use clipboard for unicode / special chars if needed
    pyautogui.write(text, interval=DELAYS["between_keys"])


def _type_clipboard(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)
    time.sleep(0.05)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(DELAYS["after_tab"])


def focus_softland_window() -> None:
    title = SOFTLAND_WINDOW_TITLE_SUBSTRING
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        # try contains
        all_w = gw.getAllWindows()
        wins = [w for w in all_w if title.lower() in (w.title or "").lower()]
    if not wins:
        raise RuntimeError(
            f"No window found matching title containing '{title}'. "
            "Set SOFTLAND_WINDOW_TITLE_SUBSTRING in config.py."
        )
    w = wins[0]
    try:
        w.activate()
    except Exception:
        w.minimize()
        w.restore()
    time.sleep(0.5)


def launch_softland_if_needed() -> None:
    exe = Path(SOFTLAND_EXE_PATH)
    if not exe.is_file():
        logger.warning(
            "SOFTLAND_EXE_PATH does not exist: %s — assuming Softland is already open.",
            exe,
        )
        return
    logger.info("Launching Softland: %s", exe)
    subprocess.Popen([str(exe)], shell=False)
    time.sleep(DELAYS["after_launch"])
    focus_softland_window()


def map_sku(shopify_sku: str) -> str:
    return SKU_MAP.get(shopify_sku, shopify_sku)


def login_if_configured(coords: dict[str, list[int]]) -> None:
    """If login_* keys exist, perform login."""
    if "login_user_xy" not in coords:
        logger.info("No login_user_xy in coords; skipping login automation.")
        return
    focus_softland_window()
    _click(coords, "login_user_xy")
    _type_clipboard(SOFTLAND_USER)
    if "login_pass_xy" in coords:
        _click(coords, "login_pass_xy")
        _type_clipboard(SOFTLAND_PASSWORD)
    if "login_ok_xy" in coords:
        _click(coords, "login_ok_xy")
    else:
        pyautogui.press("enter")
    time.sleep(DELAYS["after_launch"])


_coords_cache: dict[str, list[int]] | None = None


def initialize_session() -> dict[str, list[int]]:
    """Launch Softland, focus window, login if coords provided. Returns coords dict."""
    global _coords_cache
    _coords_cache = load_coords()
    launch_softland_if_needed()
    focus_softland_window()
    login_if_configured(_coords_cache)
    return _coords_cache


def get_coords() -> dict[str, list[int]]:
    if _coords_cache is None:
        return load_coords()
    return _coords_cache


def create_invoice_for_order(
    order: dict[str, Any],
    coords: dict[str, list[int]],
) -> None:
    """
    One invoice per Shopify order. Adjust keys to match your calibrate.py labels
    and your Softland facturación screen.
    """
    focus_softland_window()

    # Optional: open new invoice screen
    for key in ("menu_new_invoice_xy", "toolbar_new_invoice_xy"):
        if key in coords:
            _click(coords, key)
            time.sleep(DELAYS["after_tab"])
            break

    # Customer / reference — use order name as reference if field exists
    if "invoice_customer_xy" in coords:
        _click(coords, "invoice_customer_xy")
        _type_clipboard(order.get("customer_name") or "")
        time.sleep(DELAYS["after_tab"])

    if "invoice_reference_xy" in coords:
        _click(coords, "invoice_reference_xy")
        _type_clipboard(str(order.get("name") or order.get("id")))
        time.sleep(DELAYS["after_tab"])

    line_items = order.get("line_items") or []
    for i, li in enumerate(line_items):
        sku = map_sku(li.get("sku") or "")
        qty = str(li.get("quantity") or 1)

        if i > 0 and "line_next_row_xy" in coords:
            _click(coords, "line_next_row_xy")

        if "line_sku_xy" in coords:
            _click(coords, "line_sku_xy")
        elif "line_item_grid_xy" in coords and i == 0:
            _click(coords, "line_item_grid_xy")

        _type_clipboard(sku)
        time.sleep(DELAYS["after_tab"])

        if "line_qty_xy" in coords:
            _click(coords, "line_qty_xy")
            _type_clipboard(qty)
        else:
            pyautogui.press("tab")
            time.sleep(DELAYS["after_tab"])
            _type_clipboard(qty)

        time.sleep(DELAYS["after_tab"])

    # Save / post invoice
    for key in ("save_invoice_xy", "post_invoice_xy", "ok_invoice_xy"):
        if key in coords:
            _click(coords, key)
            time.sleep(DELAYS["after_invoice_save"])
            break
    else:
        logger.warning("No save_* coordinate; pressing F10 or Enter may be needed — add save_invoice_xy to coords.")


def run_order_through_softland(order: dict[str, Any]) -> None:
    coords = get_coords()
    focus_softland_window()
    create_invoice_for_order(order, coords)
