"""Gmail SMTP prototype — validates that we can replace MailerSend with
direct STARTTLS delivery via Google's submission host, without the
unique-recipient cap that blocked Arjun's send.

Usage:
    uv run --with python-dotenv python prototype.py single
    uv run --with python-dotenv python prototype.py burst 5
    uv run --with python-dotenv python prototype.py fanout
"""
from __future__ import annotations

import os
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def _load_env() -> dict:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        print("python-dotenv not available; reading .env manually", flush=True)
    else:
        load_dotenv(Path(__file__).parent / ".env")

    required = (
        "SMTP_HOST SMTP_PORT SMTP_USERNAME SMTP_PASSWORD "
        "SMTP_FROM_EMAIL TEST_RECIPIENT"
    ).split()
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing env keys: {missing}")

    return {
        "host": os.environ["SMTP_HOST"],
        "port": int(os.environ["SMTP_PORT"]),
        "username": os.environ["SMTP_USERNAME"],
        "password": os.environ["SMTP_PASSWORD"],
        "from_email": os.environ["SMTP_FROM_EMAIL"],
        "from_name": os.environ.get("SMTP_FROM_NAME", "CurateAI"),
        "test_recipient": os.environ["TEST_RECIPIENT"],
    }


def _sample_html(n: int) -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,sans-serif;background:#0f172a;color:#f8fafc;padding:24px;">
  <h2 style="color:#2dd4bf;margin:0 0 12px 0;">CurateAI — SMTP Prototype #{n}</h2>
  <p>This is test message <strong>#{n}</strong> sent via Gmail SMTP at
     {datetime.utcnow().isoformat()}Z.</p>
  <p>If you can read this, the SMTP path is working and there's no trial
     recipient allow-list blocking delivery.</p>
</body></html>"""


def send_one(cfg: dict, to_email: str, label: str, idx: int) -> float:
    """Send one message. Returns wall-clock seconds for the full round-trip."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[CurateAI prototype] {label} #{idx}"
    msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
    msg["To"] = to_email
    msg.attach(MIMEText(f"Test plain-text body {idx}", "plain"))
    msg.attach(MIMEText(_sample_html(idx), "html"))

    t0 = time.perf_counter()
    # macOS system Python sometimes ships without trusted CA roots wired
    # into stdlib ssl; fall back to certifi if available.
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ModuleNotFoundError:
        context = ssl.create_default_context()
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as s:
        s.ehlo()
        s.starttls(context=context)
        s.ehlo()
        s.login(cfg["username"], cfg["password"])
        s.sendmail(cfg["from_email"], [to_email], msg.as_string())
    return time.perf_counter() - t0


def cmd_single(cfg: dict) -> None:
    dt = send_one(cfg, cfg["test_recipient"], "single", 1)
    print(f"[ok] sent → {cfg['test_recipient']} in {dt:.2f}s", flush=True)


def cmd_burst(cfg: dict, count: int) -> None:
    print(f"Bursting {count} messages back-to-back to {cfg['test_recipient']}…")
    timings: list[float] = []
    for i in range(1, count + 1):
        try:
            dt = send_one(cfg, cfg["test_recipient"], "burst", i)
            timings.append(dt)
            print(f"  [{i}/{count}] ok in {dt:.2f}s", flush=True)
        except Exception as exc:
            print(f"  [{i}/{count}] FAIL: {type(exc).__name__}: {exc}", flush=True)
            break
    if timings:
        print(
            f"\nSent {len(timings)} / {count} — avg {sum(timings)/len(timings):.2f}s, "
            f"min {min(timings):.2f}s, max {max(timings):.2f}s",
            flush=True,
        )


def cmd_fanout(cfg: dict) -> None:
    """Send one message to each of several distinct recipients to confirm
    there's no MailerSend-style allow-list — Gmail should accept any RFC
    822 address."""
    recipients = [
        cfg["test_recipient"],       # provided by user
        cfg["from_email"],           # self-loop
        "nakka.a@northeastern.edu",  # the address MailerSend rejected
    ]
    seen = set()
    distinct = [r for r in recipients if not (r in seen or seen.add(r))]
    print(f"Fanout to {len(distinct)} distinct recipients…")
    for i, rcpt in enumerate(distinct, 1):
        try:
            dt = send_one(cfg, rcpt, "fanout", i)
            print(f"  [{i}] ok  → {rcpt}  in {dt:.2f}s", flush=True)
        except Exception as exc:
            print(f"  [{i}] FAIL → {rcpt}: {type(exc).__name__}: {exc}", flush=True)


def main(argv: list[str]) -> int:
    cfg = _load_env()
    cmd = argv[1] if len(argv) > 1 else "single"
    if cmd == "single":
        cmd_single(cfg)
    elif cmd == "burst":
        n = int(argv[2]) if len(argv) > 2 else 5
        cmd_burst(cfg, n)
    elif cmd == "fanout":
        cmd_fanout(cfg)
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
