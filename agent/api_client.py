"""Generic REST/GraphQL client. Headers/auth pull from the vault by name when needed."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from agent.credential_vault import get_credential


def _resolve_auth(auth_name: str) -> dict:
    """Pull credential by name, return appropriate header dict.
    Convention:
      vault key 'api_<name>'        → Bearer token
      vault key 'api_<name>_basic'  → already base64-encoded basic auth
      vault key 'api_<name>_header' → JSON dict of headers
    """
    if not auth_name:
        return {}
    bearer = get_credential(f"api_{auth_name}")
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}
    basic = get_credential(f"api_{auth_name}_basic")
    if basic:
        return {"Authorization": f"Basic {basic}"}
    raw = get_credential(f"api_{auth_name}_header")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


@tool
def http_get(url: str, auth_name: str = "", params: str = "") -> str:
    """HTTP GET. auth_name: vault key suffix to inject auth header. params: JSON query params."""
    try:
        import requests
    except ImportError:
        return "[error] pip install requests"
    headers = _resolve_auth(auth_name) | {"User-Agent": "Ultron/3"}
    p = json.loads(params) if params.strip() else None
    try:
        r = requests.get(url, headers=headers, params=p, timeout=30)
        return f"[{r.status_code}] {r.text[:5000]}"
    except Exception as e:
        return f"[error] {e}"


@tool
def http_post(url: str, body: str, auth_name: str = "", content_type: str = "application/json") -> str:
    """HTTP POST. body is sent as-is. content_type defaults to JSON."""
    try:
        import requests
    except ImportError:
        return "[error] pip install requests"
    headers = _resolve_auth(auth_name) | {
        "User-Agent": "Ultron/3", "Content-Type": content_type,
    }
    try:
        r = requests.post(url, headers=headers, data=body, timeout=30)
        return f"[{r.status_code}] {r.text[:5000]}"
    except Exception as e:
        return f"[error] {e}"


@tool
def http_put(url: str, body: str, auth_name: str = "", content_type: str = "application/json") -> str:
    """HTTP PUT."""
    try:
        import requests
    except ImportError:
        return "[error] pip install requests"
    headers = _resolve_auth(auth_name) | {"User-Agent": "Ultron/3", "Content-Type": content_type}
    try:
        r = requests.put(url, headers=headers, data=body, timeout=30)
        return f"[{r.status_code}] {r.text[:3000]}"
    except Exception as e:
        return f"[error] {e}"


@tool
def http_delete(url: str, auth_name: str = "") -> str:
    """HTTP DELETE."""
    try:
        import requests
    except ImportError:
        return "[error] pip install requests"
    headers = _resolve_auth(auth_name) | {"User-Agent": "Ultron/3"}
    try:
        r = requests.delete(url, headers=headers, timeout=30)
        return f"[{r.status_code}] {r.text[:1500]}"
    except Exception as e:
        return f"[error] {e}"


@tool
def graphql_query(url: str, query: str, variables: str = "{}", auth_name: str = "") -> str:
    """Run a GraphQL query. variables: JSON string of variables map."""
    try:
        import requests
    except ImportError:
        return "[error] pip install requests"
    headers = _resolve_auth(auth_name) | {
        "User-Agent": "Ultron/3", "Content-Type": "application/json",
    }
    try:
        vars_obj = json.loads(variables) if variables.strip() else {}
    except json.JSONDecodeError as e:
        return f"[error] variables not valid JSON: {e}"
    body = json.dumps({"query": query, "variables": vars_obj})
    try:
        r = requests.post(url, headers=headers, data=body, timeout=30)
        return f"[{r.status_code}] {r.text[:5000]}"
    except Exception as e:
        return f"[error] {e}"


API_CLIENT_TOOLS = [http_get, http_post, http_put, http_delete, graphql_query]
