"""Real browser automation via Playwright. Fill forms, click, screenshot, scrape rendered pages.

Sessions are persistent — login state is preserved across calls (stored in data/playwright/).
First call boots Chromium (~3s); subsequent calls are fast."""
from __future__ import annotations

import threading
from pathlib import Path

from langchain_core.tools import tool

from config import DATA_DIR


PROFILE_DIR = DATA_DIR / "playwright"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


class _BrowserSession:
    def __init__(self):
        self._lock = threading.Lock()
        self._pw = None
        self._ctx = None
        self._page = None

    def _ensure(self):
        if self._page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("install: pip install playwright && python -m playwright install chromium")

        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()

    def page(self):
        with self._lock:
            self._ensure()
            return self._page

    def close(self):
        with self._lock:
            try:
                if self._ctx: self._ctx.close()
                if self._pw: self._pw.stop()
            except Exception:
                pass
            self._pw = self._ctx = self._page = None


_session = _BrowserSession()


@tool
def browser_open(url: str) -> str:
    """Open a URL in the persistent browser session (preserves logins). Returns page title."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        page = _session.page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return f"✓ {page.title()} ({page.url})"
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_click(selector: str) -> str:
    """Click an element. selector: CSS or text="...".  e.g. 'button.login' or 'text=Submit'."""
    try:
        page = _session.page()
        page.click(selector, timeout=10_000)
        return f"✓ clicked {selector}"
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_fill(selector: str, value: str) -> str:
    """Type text into a form input. selector: CSS, e.g. 'input[name=q]' or '#email'."""
    try:
        page = _session.page()
        page.fill(selector, value, timeout=10_000)
        return f"✓ filled {selector}"
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_press(key: str) -> str:
    """Press a key in the focused element (Enter, Tab, ArrowDown, etc.)."""
    try:
        page = _session.page()
        page.keyboard.press(key)
        return f"✓ pressed {key}"
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_text() -> str:
    """Get all visible text from the current page (max 6000 chars)."""
    try:
        page = _session.page()
        text = page.evaluate("() => document.body.innerText")
        return (text[:6000] + "…") if len(text) > 6000 else text
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_screenshot(filename: str = "browser.png") -> str:
    """Save a screenshot of the current page to ~/Pictures/Ultron/."""
    out_dir = Path.home() / "Pictures" / "Ultron"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".png"):
        filename += ".png"
    dest = out_dir / filename
    try:
        page = _session.page()
        page.screenshot(path=str(dest), full_page=True)
        return f"✓ {dest}"
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_eval(js: str) -> str:
    """Run a JavaScript expression on the current page. Return its result as a string."""
    try:
        page = _session.page()
        result = page.evaluate(f"() => {{ try {{ return ({js}); }} catch(e) {{ return String(e); }} }}")
        return str(result)[:2000]
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_url() -> str:
    """Get the current browser URL."""
    try:
        return _session.page().url
    except Exception as e:
        return f"[error] {e}"


@tool
def browser_close() -> str:
    """Close the browser session."""
    _session.close()
    return "✓ closed"


BROWSER_TOOLS = [
    browser_open, browser_click, browser_fill, browser_press,
    browser_text, browser_screenshot, browser_eval, browser_url, browser_close,
]
