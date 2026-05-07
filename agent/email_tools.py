"""Real email — IMAP read + SMTP send. Credentials live in OS keyring (vault).

Setup once via the Vault UI:
- email_address    → your address
- email_password   → app password (NOT your normal one — for Gmail use App Passwords)
- imap_host        → e.g. imap.gmail.com
- smtp_host        → e.g. smtp.gmail.com
- smtp_port        → e.g. 587"""
from __future__ import annotations

import email
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

from langchain_core.tools import tool

from agent.credential_vault import get_credential


def _creds() -> tuple[str, str, str, str, int] | None:
    addr = get_credential("email_address")
    pwd = get_credential("email_password")
    imap = get_credential("imap_host") or "imap.gmail.com"
    smtp = get_credential("smtp_host") or "smtp.gmail.com"
    port = get_credential("smtp_port") or "587"
    if not (addr and pwd):
        return None
    try:
        return addr, pwd, imap, smtp, int(port)
    except ValueError:
        return None


@tool
def email_inbox(folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> str:
    """Read the inbox. limit: number of messages, latest first. unread_only: only UNREAD."""
    c = _creds()
    if not c:
        return "[error] set email_address + email_password (and imap_host) in the Vault first"
    addr, pwd, imap_host, _, _ = c
    try:
        m = imaplib.IMAP4_SSL(imap_host)
        m.login(addr, pwd)
        m.select(folder, readonly=True)
        criterion = "(UNSEEN)" if unread_only else "ALL"
        typ, data = m.search(None, criterion)
        ids = data[0].split()[-limit:][::-1]
        out = []
        for mid in ids:
            typ, msg_data = m.fetch(mid, "(RFC822.HEADER)")
            msg = email.message_from_bytes(msg_data[0][1])
            sender = parseaddr(msg.get("From", ""))[1]
            subject = msg.get("Subject", "(no subject)")
            date = msg.get("Date", "")
            out.append(f"#{mid.decode()}  [{date[:25]}]  {sender}\n  → {subject}")
        m.logout()
        return "\n\n".join(out) or "(empty)"
    except Exception as e:
        return f"[error] {e}"


@tool
def email_read(message_id: str) -> str:
    """Read the body of a specific email by its IMAP id (from email_inbox)."""
    c = _creds()
    if not c:
        return "[error] set email credentials in the Vault first"
    addr, pwd, imap_host, _, _ = c
    try:
        m = imaplib.IMAP4_SSL(imap_host)
        m.login(addr, pwd)
        m.select("INBOX", readonly=True)
        typ, data = m.fetch(message_id.encode(), "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        sender = msg.get("From", "")
        subject = msg.get("Subject", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            body = payload.decode(errors="ignore") if payload else ""
        m.logout()
        return f"From: {sender}\nSubject: {subject}\n\n{body[:4000]}"
    except Exception as e:
        return f"[error] {e}"


@tool
def email_send(to: str, subject: str, body: str, cc: str = "") -> str:
    """Actually send an email via SMTP. Uses credentials from the Vault.
    For Gmail: use an App Password, not your account password."""
    c = _creds()
    if not c:
        return "[error] set email_address + email_password + smtp_host in the Vault first"
    addr, pwd, _, smtp_host, smtp_port = c
    msg = MIMEMultipart()
    msg["From"] = addr
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    recipients = [to] + ([cc] if cc else [])
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
            s.starttls()
            s.login(addr, pwd)
            s.sendmail(addr, recipients, msg.as_string())
        return f"✓ sent to {to}" + (f", cc {cc}" if cc else "")
    except Exception as e:
        return f"[error] {e}"


@tool
def email_search(query: str, limit: int = 10) -> str:
    """Search the inbox. query is an IMAP search like 'FROM boss@x.com' or 'SUBJECT invoice'."""
    c = _creds()
    if not c:
        return "[error] set email credentials in the Vault first"
    addr, pwd, imap_host, _, _ = c
    try:
        m = imaplib.IMAP4_SSL(imap_host)
        m.login(addr, pwd)
        m.select("INBOX", readonly=True)
        typ, data = m.search(None, query)
        ids = data[0].split()[-limit:][::-1]
        out = []
        for mid in ids:
            typ, msg_data = m.fetch(mid, "(RFC822.HEADER)")
            msg = email.message_from_bytes(msg_data[0][1])
            out.append(f"#{mid.decode()}  {msg.get('From','')}  → {msg.get('Subject','')}")
        m.logout()
        return "\n".join(out) or "(no results)"
    except Exception as e:
        return f"[error] {e}"


EMAIL_TOOLS = [email_inbox, email_read, email_send, email_search]
