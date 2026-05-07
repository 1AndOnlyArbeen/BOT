"""Communication tools: open compose windows for WhatsApp / Telegram / Email / SMS / social.
The user reviews + sends in the actual app — agent never sends without confirmation."""
from __future__ import annotations

import subprocess
import urllib.parse

from langchain_core.tools import tool


def _xdg(url: str) -> str:
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"✓ opened {url[:80]}"
    except FileNotFoundError:
        return "[error] xdg-open not available"
    except Exception as e:
        return f"[error] {e}"


@tool
def whatsapp_message(phone: str, message: str = "") -> str:
    """Open WhatsApp Web (or app) with a prefilled message to a phone number.
    phone: international format like '+9779812345678' or '9779812345678' (no spaces)."""
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return "[error] phone must contain digits"
    text = urllib.parse.quote(message)
    url = f"https://wa.me/{digits}?text={text}" if message else f"https://wa.me/{digits}"
    return _xdg(url)


@tool
def telegram_message(username: str, message: str = "") -> str:
    """Open Telegram chat with @username and prefill a message."""
    username = username.lstrip("@")
    text = urllib.parse.quote(message)
    url = f"https://t.me/{username}" + (f"?text={text}" if message else "")
    return _xdg(url)


@tool
def email_compose(to: str, subject: str = "", body: str = "") -> str:
    """Open the default mail client with a prefilled message."""
    params = []
    if subject:
        params.append(f"subject={urllib.parse.quote(subject)}")
    if body:
        params.append(f"body={urllib.parse.quote(body)}")
    qs = ("?" + "&".join(params)) if params else ""
    return _xdg(f"mailto:{to}{qs}")


@tool
def sms_message(phone: str, message: str = "") -> str:
    """Open SMS client with a prefilled message (uses sms: URI)."""
    digits = "".join(c for c in phone if c.isdigit() or c == "+")
    text = urllib.parse.quote(message)
    return _xdg(f"sms:{digits}?body={text}" if message else f"sms:{digits}")


@tool
def google_search(query: str) -> str:
    """Open a Google search in the browser."""
    return _xdg(f"https://www.google.com/search?q={urllib.parse.quote(query)}")


@tool
def youtube_search(query: str) -> str:
    """Open a YouTube search in the browser."""
    return _xdg(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")


@tool
def open_facebook(target: str = "") -> str:
    """Open Facebook. target: empty for home, or a profile/page name like 'zuck'."""
    url = "https://www.facebook.com/"
    if target:
        url += target.lstrip("/")
    return _xdg(url)


@tool
def facebook_message(name: str) -> str:
    """Open Facebook Messenger to start a conversation. name: profile name or username."""
    return _xdg(f"https://www.messenger.com/t/{urllib.parse.quote(name)}")


@tool
def open_instagram(target: str = "") -> str:
    """Open Instagram. target: empty for feed, or a username."""
    url = "https://www.instagram.com/"
    if target:
        url += target.lstrip("@").rstrip("/") + "/"
    return _xdg(url)


@tool
def open_linkedin(target: str = "") -> str:
    """Open LinkedIn. target: empty for feed, or '/in/username'."""
    url = "https://www.linkedin.com"
    if target:
        if not target.startswith("/"):
            target = "/in/" + target
        url += target
    return _xdg(url)


@tool
def open_twitter(target: str = "") -> str:
    """Open Twitter/X. target: empty for home, or '@username' to view a profile."""
    url = "https://twitter.com/"
    if target:
        url += target.lstrip("@")
    return _xdg(url)


@tool
def post_tweet(text: str) -> str:
    """Open Twitter compose with prefilled text."""
    return _xdg(f"https://twitter.com/intent/tweet?text={urllib.parse.quote(text)}")


@tool
def open_maps(query: str) -> str:
    """Open Google Maps with a search query (location, place, directions)."""
    return _xdg(f"https://www.google.com/maps/search/{urllib.parse.quote(query)}")


COMM_TOOLS = [
    whatsapp_message, telegram_message,
    email_compose, sms_message,
    google_search, youtube_search,
    open_facebook, facebook_message,
    open_instagram, open_linkedin,
    open_twitter, post_tweet,
    open_maps,
]
