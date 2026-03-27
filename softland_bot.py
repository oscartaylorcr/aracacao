"""
Softland ERP UI automation using calibrated screen coordinates.
Requires coords_captured.json from calibrate.py on this machine.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pyautogui
import pygetwindow as gw

import config as app_config

logger = logging.getLogger(__name__)

COORDS_FILE = app_config.COORDS_FILE
PYAUTOGUI_FAILSAFE = app_config.PYAUTOGUI_FAILSAFE
SKU_MAP = app_config.SKU_MAP
SOFTLAND_EXE_PATH = app_config.SOFTLAND_EXE_PATH
SOFTLAND_PASSWORD = app_config.SOFTLAND_PASSWORD
SOFTLAND_USER = app_config.SOFTLAND_USER
SOFTLAND_WINDOW_TITLE_SUBSTRING = app_config.SOFTLAND_WINDOW_TITLE_SUBSTRING
WINDOWS_APP_EXE_PATH = getattr(
    app_config,
    "WINDOWS_APP_EXE_PATH",
    os.environ.get(
        "WINDOWS_APP_EXE_PATH",
        r"C:\Program Files\WindowsApps\MicrosoftCorporationII.WindowsApp_...\Windows App.exe",
    ),
)
WINDOWS_APP_WINDOW_TITLE_SUBSTRING = getattr(
    app_config,
    "WINDOWS_APP_WINDOW_TITLE_SUBSTRING",
    os.environ.get("WINDOWS_APP_WINDOW_TITLE_SUBSTRING", "Windows App"),
)
DELAYS = {
    "after_launch": 12.0,
    "after_windows_app_launch": 8.0,
    "after_portal_launch": 10.0,
    "after_erp_launch": 8.0,
    "between_keys": 0.05,
    "between_clicks": 0.4,
    "after_tab": 0.2,
    "after_invoice_save": 2.0,
}
DELAYS.update(getattr(app_config, "DELAYS", {}))

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


def _focus_window(title: str, missing_message: str) -> None:
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        # try contains
        all_w = gw.getAllWindows()
        wins = [w for w in all_w if title.lower() in (w.title or "").lower()]
    if not wins:
        raise RuntimeError(missing_message)
    w = wins[0]
    try:
        w.activate()
    except Exception:
        w.minimize()
        w.restore()
    time.sleep(0.5)


def focus_softland_window() -> None:
    _focus_window(
        SOFTLAND_WINDOW_TITLE_SUBSTRING,
        f"No window found matching title containing '{SOFTLAND_WINDOW_TITLE_SUBSTRING}'. "
        "Set SOFTLAND_WINDOW_TITLE_SUBSTRING in config.py.",
    )


def focus_windows_app_window() -> None:
    _focus_window(
        WINDOWS_APP_WINDOW_TITLE_SUBSTRING,
        f"No window found matching title containing '{WINDOWS_APP_WINDOW_TITLE_SUBSTRING}'. "
        "Set WINDOWS_APP_WINDOW_TITLE_SUBSTRING in config.py.",
    )


def launch_local_softland_if_needed() -> bool:
    exe = Path(SOFTLAND_EXE_PATH)
    if not exe.is_file():
        return False
    logger.info("Launching Softland: %s", exe)
    subprocess.Popen([str(exe)], shell=False)
    time.sleep(DELAYS["after_launch"])
    focus_softland_window()
    return True


def launch_windows_app_if_needed() -> bool:
    exe = Path(WINDOWS_APP_EXE_PATH)
    if not exe.is_file():
        return False
    logger.info("Launching Windows App: %s", exe)
    subprocess.Popen([str(exe)], shell=False)
    time.sleep(DELAYS["after_windows_app_launch"])
    focus_windows_app_window()
    return True


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
    time.sleep(DELAYS["after_erp_launch"])


def open_softland_via_windows_app(coords: dict[str, list[int]]) -> None:
    """
    Optional bootstrap flow for remote Softland access:
    Windows App -> Aplicaciones -> Softland Cloud -> Programas -> Softland ERP
    """
    used_windows_app_flow = any(
        key in coords
        for key in (
            "windows_app_apps_xy",
            "windows_app_softland_cloud_xy",
            "portal_programas_xy",
            "portal_softland_erp_xy",
        )
    )
    if not used_windows_app_flow:
        return

    windows_app_started = launch_windows_app_if_needed()
    if windows_app_started or "windows_app_apps_xy" in coords:
        focus_windows_app_window()

    if "windows_app_apps_xy" in coords:
        _click(coords, "windows_app_apps_xy")
        time.sleep(DELAYS["after_tab"])

    if "windows_app_softland_cloud_xy" in coords:
        _click(coords, "windows_app_softland_cloud_xy")
        time.sleep(DELAYS["after_portal_launch"])

    focus_softland_window()

    if "portal_programas_xy" in coords:
        _click(coords, "portal_programas_xy")
        time.sleep(DELAYS["after_tab"])

    if "portal_softland_erp_xy" in coords:
        _click(coords, "portal_softland_erp_xy")
        time.sleep(DELAYS["after_erp_launch"])

    focus_softland_window()


def navigate_to_facturacion_if_configured(coords: dict[str, list[int]]) -> None:
    if "menu_facturacion_xy" not in coords:
        logger.info("No menu_facturacion_xy in coords; assuming Facturacion is already open.")
        return
    focus_softland_window()
    _click(coords, "menu_facturacion_xy")
    time.sleep(DELAYS["after_tab"])


_coords_cache: dict[str, list[int]] | None = None


def initialize_session() -> dict[str, list[int]]:
    """Open Softland session, optionally via Windows App / portal, and navigate to Facturacion."""
    global _coords_cache
    _coords_cache = load_coords()
    launched_locally = launch_local_softland_if_needed()
    if not launched_locally:
        open_softland_via_windows_app(_coords_cache)
    focus_softland_window()
    login_if_configured(_coords_cache)
    navigate_to_facturacion_if_configured(_coords_cache)
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
