"""Send a plaintext email via Gmail SMTP (app password).

Used by the weekend autonomous runs to report progress / questions. Credentials
come from the repo .env (gitignored):

  GMAIL_ADDRESS       sender + default recipient (e.g. you@gmail.com)
  GMAIL_APP_PASSWORD  16-char Google *app password* (NOT your login password)
  GMAIL_TO            optional recipient override (defaults to GMAIL_ADDRESS)

Usage:
  python tools/send_email.py --subject "Buttery Fri AM" --body-file summary.txt
  echo "hello" | python tools/send_email.py --subject "test"
"""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body-file", help="read body from this file; else read stdin")
    ap.add_argument("--to", help="override recipient")
    args = ap.parse_args()

    sender = os.getenv("GMAIL_ADDRESS")
    pw = os.getenv("GMAIL_APP_PASSWORD")
    recipient = args.to or os.getenv("GMAIL_TO") or sender
    if not sender or not pw:
        print("Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in .env", file=sys.stderr)
        return 2
    pw = pw.replace(" ", "")  # Google shows the app password in 4x4 groups

    body = (
        open(args.body_file, encoding="utf-8").read()
        if args.body_file else sys.stdin.read()
    )

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = args.subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(sender, pw)
        s.send_message(msg)
    print(f"Sent '{args.subject}' -> {recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
