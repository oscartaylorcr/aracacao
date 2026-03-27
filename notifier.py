"""
Optional SMTP email summary after each run.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from config import (
    EMAIL_FROM,
    EMAIL_TO,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(SMTP_HOST and EMAIL_FROM and EMAIL_TO)


def send_summary(subject: str, body: str, html: str | None = None) -> None:
    if not is_configured():
        logger.info("Email not configured; skipping notification.")
        return

    recipients = [e.strip() for e in EMAIL_TO.split(",") if e.strip()]
    if not recipients:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            if SMTP_USE_TLS:
                server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Sent email summary to %s", recipients)
    except Exception:
        logger.exception("Failed to send email notification")


def format_run_summary(results: list[dict[str, Any]]) -> tuple[str, str]:
    """Plain + simple HTML summary."""
    lines = []
    for r in results:
        oid = r.get("order_id")
        name = r.get("order_name", "")
        status = r.get("status", "unknown")
        err = r.get("error") or ""
        lines.append(f"- {name} (id={oid}): {status}" + (f" — {err}" if err else ""))

    plain = "Shopify → Softland run\n\n" + "\n".join(lines) if lines else "No orders processed."
    rows = "".join(
        f"<tr><td>{r.get('order_name','')}</td><td>{r.get('status')}</td><td>{r.get('error') or ''}</td></tr>"
        for r in results
    )
    html = f"""<html><body><h3>Shopify → Softland</h3><table border="1"><tr><th>Order</th><th>Status</th><th>Error</th></tr>{rows}</table></body></html>"""
    return plain, html
