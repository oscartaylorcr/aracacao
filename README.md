# Shopify → Softland ERP (Windows automation)

Python automation that:

1. Pulls **purchase orders** from **Shopify Admin API** (REST).
2. Creates **invoices** in **Softland** via **mouse/keyboard automation** (pyautogui) using **calibrated screen coordinates**.

**Important:** This does **not** use Claude Computer Use or the Claude consumer subscription. It uses Shopify’s API plus local UI automation. Your **Shopify Admin API token** is required.

---

## Prerequisites (confirm with the client)

| Item | Notes |
|------|--------|
| Windows 10/11 | Task Scheduler is used for the daily run |
| Python **3.10+** | [python.org](https://www.python.org/downloads/) — check “Add Python to PATH” during install |
| Softland ERP | Installed; you know the **.exe** path and **window title** substring |
| Internet | For Shopify API |
| Shopify | **Admin API** access token (Custom app in Shopify Admin) |
| SMTP (optional) | For email summary after each run |

---

## Meeting-day install order

### 1) Copy the project

Place the folder on the client PC, e.g. `C:\SolarpunkSync\`

### 2) Create a virtual environment (recommended)

```bat
cd C:\SolarpunkSync
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Or globally:

```bat
pip install -r requirements.txt
```

### 3) Configure `config.py` (or environment variables)

Edit `config.py` on the client machine (or set env vars — see file for names):

- **SHOPIFY_SHOP** — store subdomain, e.g. `my-store` or `my-store.myshopify.com`
- **SHOPIFY_ACCESS_TOKEN** — Admin API token
- **SOFTLAND_EXE_PATH** — full path to Softland’s `.exe`
- **SOFTLAND_WINDOW_TITLE_SUBSTRING** — unique part of the window title (use Task Manager / hover taskbar to confirm)
- **SOFTLAND_USER** / **SOFTLAND_PASSWORD** — if login is automated via calibration
- **DELAYS** — if the PC is slow, increase `after_launch` (e.g. `12`–`15` seconds)
- **SKU_MAP** — map Shopify SKUs to Softland product codes if they differ

**Shopify token:** In Shopify Admin → Settings → Apps → Develop apps → create a custom app → Admin API scopes: at minimum `read_orders` (and any scopes needed for your order data).

### 4) Preflight check (no Softland clicks)

```bat
python main.py --verify
```

You should see the Shopify shop name. If the Softland path is wrong, you’ll get a warning (OK if Softland will be opened manually).

### 5) Calibrate coordinates (critical on-site step)

1. Open **Softland** manually to the screens you need (login + facturación / new invoice).
2. Run:

```bat
python calibrate.py
```

3. For each prompt, **move the mouse** to the correct control and press **Enter**.
4. This writes **`coords_captured.json`** next to `main.py`.

You can re-run `calibrate.py` to overwrite; it merges with existing keys if the file already exists.

### 6) Dry run (Shopify fetch only, no clicks)

```bat
python main.py --dry-run
```

Confirms orders are retrieved and logs what would be entered. **No Softland automation** runs.

### 7) Live test (one manual run)

1. Open Softland and log in if needed.
2. Run:

```bat
python main.py
```

3. Watch the screen; stop with mouse in top-left corner if **pyautogui failsafe** is on (default).
4. Read **`automation.log`** for details.

### 8) Schedule daily run (e.g. 6:00 AM)

1. Open **Task Scheduler** → **Create Task** (not “Create Basic Task”).
2. **General:** Run whether user is logged on or not; Run with highest privileges (if required for Softland).
3. **Triggers:** Daily, 6:00:00 AM (adjust as needed).
4. **Actions:** Start a program  
   - Program: `cmd.exe`  
   - Arguments: `/c "C:\SolarpunkSync\run_sync.bat"`  
   - Start in: `C:\SolarpunkSync`
5. If you use a venv, edit `run_sync.bat` to call the venv’s `python.exe` instead of `python`.

**Test the task:** Right-click the task → **Run** → check `automation.log`.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | Credentials, paths, delays, SKU map |
| `shopify_client.py` | Shopify REST: fetch orders |
| `softland_bot.py` | Launch/focus Softland, login, invoice entry from coords |
| `calibrate.py` | Build `coords_captured.json` |
| `notifier.py` | Optional SMTP summary |
| `main.py` | Orchestration, duplicate protection (`processed_orders.json`) |
| `run_sync.bat` | Wrapper for Task Scheduler |
| `requirements.txt` | Python dependencies |

---

## Duplicate protection

Processed Shopify order IDs are stored in **`processed_orders.json`**. To **re-process** an order, remove its ID from that file (or delete the file — not recommended in production).

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| “Missing coords_captured.json” | Run `calibrate.py` |
| Clicks land in wrong place | Re-run calibration; check **display scaling** (100% vs 125%); avoid RDP if coordinates differ |
| Window not found | Fix `SOFTLAND_WINDOW_TITLE_SUBSTRING` to match the real title |
| Shopify 401/403 | Token scopes or wrong shop subdomain |
| No orders fetched | Adjust `SHOPIFY_LOOKBACK_HOURS`, `SHOPIFY_FINANCIAL_STATUS`, or order payment status |
| Wrong product lines | Align **SKU** in Shopify with Softland or use `SKU_MAP` in `config.py` |

---

## Security

- Do **not** commit `coords_captured.json`, `processed_orders.json`, or real credentials.
- Restrict file permissions on the folder on the client PC to trusted users.
- Rotate Shopify API tokens if exposed.

---

## License

Use and modify for your client deployment as needed.
