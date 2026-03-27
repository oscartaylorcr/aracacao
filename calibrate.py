"""
Interactive calibration: move mouse to each UI element, press Enter to capture (x, y).
Writes coords_captured.json for softland_bot.py.

Run with Softland visible (e.g. on login or facturación screen as needed).
"""
from __future__ import annotations

import json
import sys
import time

import pyautogui

from config import COORDS_FILE, PYAUTOGUI_FAILSAFE

pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE

# Keys used by softland_bot.py — calibrate the ones you need; you can skip optional keys
# by editing the JSON afterward or pressing Enter without moving (not recommended).
CALIBRATION_STEPS: list[tuple[str, str]] = [
    ("login_user_xy", "Login: click field for USERNAME (skip if already logged in — press Enter at center of screen)"),
    ("login_pass_xy", "Login: PASSWORD field"),
    ("login_ok_xy", "Login: OK / Entrar button"),
    ("menu_new_invoice_xy", "Facturación: menu or button to create NEW invoice (optional if you use toolbar)"),
    ("toolbar_new_invoice_xy", "Toolbar shortcut for new invoice (optional)"),
    ("invoice_customer_xy", "Invoice header: CUSTOMER / cliente field"),
    ("invoice_reference_xy", "Invoice: REFERENCE / pedido / comentario (Shopify order name)"),
    ("line_sku_xy", "First line: PRODUCT / SKU / código field"),
    ("line_qty_xy", "First line: QTY (if separate field; else use Tab from SKU)"),
    ("line_next_row_xy", "Add next line / next row (optional, for multi-line orders)"),
    ("save_invoice_xy", "SAVE / POST / Guardar factura button"),
]


def main() -> None:
    print("Softland coordinate calibration")
    print(f"Output file: {COORDS_FILE}")
    print("For each step: move the mouse to the correct spot, then press Enter.")
    print("Type 'q' + Enter to quit and save what you have so far.\n")

    out: dict[str, list[int]] = {}
    if COORDS_FILE.is_file():
        try:
            with open(COORDS_FILE, encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                out.update({k: v for k, v in existing.items() if isinstance(v, list) and len(v) >= 2})
                print(f"Loaded {len(out)} existing coordinates. You can overwrite.\n")
        except Exception:
            pass

    for key, hint in CALIBRATION_STEPS:
        print(f"\n[{key}]")
        print(f"  {hint}")
        s = input("  Press Enter to capture mouse position (or 's' to skip, 'q' to quit): ").strip().lower()
        if s == "q":
            break
        if s == "s":
            continue
        time.sleep(0.3)
        x, y = pyautogui.position()
        out[key] = [int(x), int(y)]
        print(f"  -> saved {key} = [{x}, {y}]")

    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {len(out)} coordinates to {COORDS_FILE}")
    print("Next: set SOFTLAND_WINDOW_TITLE_SUBSTRING and test with: python main.py --dry-run then python main.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
