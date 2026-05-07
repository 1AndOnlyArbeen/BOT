"""Web fetch + scrape. Read pages, extract text/links/images, download files."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from langchain_core.tools import tool


def _normalize(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


@tool
def fetch_url(url: str) -> str:
    """Fetch a URL and return readable text content (HTML stripped, max 8000 chars)."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return "[error] install requests and beautifulsoup4"

    url = _normalize(url)
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Ultron/1.0"})
        r.raise_for_status()
    except Exception as e:
        return f"[error] {e}"

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = "\n".join(line for line in text.split("\n") if line.strip())
    return (text[:8000] + "…") if len(text) > 8000 else text


@tool
def fetch_links(url: str) -> str:
    """Get all hyperlinks from a webpage."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return "[error] install requests and beautifulsoup4"

    url = _normalize(url)
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Ultron/1.0"})
    except Exception as e:
        return f"[error] {e}"

    soup = BeautifulSoup(r.text, "html.parser")
    seen = set()
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)[:60]
        if href.startswith("#") or href in seen:
            continue
        seen.add(href)
        out.append(f"{text or '(no text)'}: {href}")
        if len(out) >= 50:
            break
    return "\n".join(out) or "(no links)"


@tool
def download_file(url: str, save_as: str = "") -> str:
    """Download a file from URL to ~/Downloads/. save_as: optional filename."""
    try:
        import requests
    except ImportError:
        return "[error] install requests"

    url = _normalize(url)
    dest_dir = Path.home() / "Downloads"
    dest_dir.mkdir(exist_ok=True)

    if not save_as:
        save_as = Path(urlparse(url).path).name or "download.bin"
    dest = dest_dir / save_as

    try:
        with requests.get(url, stream=True, timeout=30, headers={"User-Agent": "Ultron/1.0"}) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
    except Exception as e:
        return f"[error] {e}"
    return f"✓ saved to {dest} ({dest.stat().st_size} bytes)"


@tool
def get_public_ip() -> str:
    """Get this machine's public IP address."""
    try:
        import requests
        return requests.get("https://api.ipify.org", timeout=10).text.strip()
    except Exception as e:
        return f"[error] {e}"


WEB_FETCH_TOOLS = [fetch_url, fetch_links, download_file, get_public_ip]
