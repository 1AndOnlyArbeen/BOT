"""Encrypted credential vault using OS keyring (libsecret/Keychain/Windows Credential Manager).

The agent CANNOT read these directly — only the user-facing UI/api can. Tools that need
credentials request them by name from this module."""
from __future__ import annotations

import json
from pathlib import Path

from config import DATA_DIR


SERVICE_NAME = "ultron-vault"
INDEX_FILE = DATA_DIR / "vault_index.json"


def _index() -> dict:
    if not INDEX_FILE.exists():
        return {}
    try:
        return json.loads(INDEX_FILE.read_text())
    except Exception:
        return {}


def _save_index(idx: dict) -> None:
    INDEX_FILE.write_text(json.dumps(idx, indent=2))


def set_credential(name: str, value: str, kind: str = "secret") -> bool:
    """Store a credential in the OS keyring."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, name, value)
    except Exception:
        return False
    idx = _index()
    idx[name] = {"kind": kind}
    _save_index(idx)
    return True


def get_credential(name: str) -> str | None:
    try:
        import keyring
        return keyring.get_password(SERVICE_NAME, name)
    except Exception:
        return None


def delete_credential(name: str) -> bool:
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, name)
    except Exception:
        return False
    idx = _index()
    if name in idx:
        del idx[name]
        _save_index(idx)
    return True


def list_credentials() -> list[dict]:
    """Return metadata only — never values."""
    idx = _index()
    return [{"name": k, **v} for k, v in idx.items()]
