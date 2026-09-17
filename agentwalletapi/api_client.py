"""Thin HTTP client for the OpenClawCash agent API.

Mirrors mcp-server/openclawcash-mcp.mjs: same env var names and fallbacks,
same default base URL, and the same host allowlist. The allowlist exists
because the base URL is read from the environment (and from .env-style
config), so a tampered value could otherwise redirect the agent key to an
attacker-controlled host.
"""

from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://openclawcash.com"
_HOST_PATTERN = re.compile(r"^openclawcash\.com$|^[a-z0-9-]+\.openclawcash\.com$")
_TIMEOUT_SECONDS = 30


class AgentWalletApiError(Exception):
    def __init__(self, message: str, *, status: int | None = None, body: dict | None = None):
        super().__init__(message)
        self.status = status
        self.body = body or {}


def _get_env(name: str, fallback_names: tuple[str, ...] = ()) -> str | None:
    for key in (name, *fallback_names):
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return None


def get_agent_key() -> str:
    key = _get_env("OPENCLAWCASH_AGENT_KEY", ("AGENTWALLETAPI_KEY",))
    if not key:
        raise AgentWalletApiError(
            "Missing OpenClawCash agent key. Set OPENCLAWCASH_AGENT_KEY (or AGENTWALLETAPI_KEY) "
            "in the environment before using this plugin."
        )
    return key


def get_base_url() -> str:
    raw = (_get_env("OPENCLAWCASH_BASE_URL", ("AGENTWALLETAPI_URL",)) or DEFAULT_BASE_URL).rstrip("/")
    if not raw.startswith("https://"):
        raise AgentWalletApiError(f"OPENCLAWCASH_BASE_URL must be https. Got: {raw}")
    rest = raw[len("https://") :]
    if "@" in rest or "/" in rest:
        raise AgentWalletApiError(f"OPENCLAWCASH_BASE_URL must not contain a path, port, or credentials. Got: {raw}")
    host = rest.split(":")[0]
    if ":" in rest or not _HOST_PATTERN.match(host):
        raise AgentWalletApiError(
            f"OPENCLAWCASH_BASE_URL must be https://openclawcash.com or an https://<subdomain>.openclawcash.com "
            f"host (no port). Refusing to send the agent key to untrusted host: {raw}"
        )
    return raw


def call_agent_api(method: str, path: str, *, query: dict | None = None, body: dict | None = None) -> dict:
    """Call an authenticated /api/agent/* endpoint. Raises AgentWalletApiError on failure."""
    base_url = get_base_url()
    agent_key = get_agent_key()

    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v is not None}
        if clean:
            from urllib.parse import urlencode

            url = f"{url}?{urlencode(clean)}"

    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "X-Agent-Key": agent_key}
    if data is not None:
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
            return payload
    except HTTPError as err:
        try:
            payload = json.loads(err.read().decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            payload = {"message": str(err)}
        raise AgentWalletApiError(
            payload.get("message") or f"HTTP {err.code}", status=err.code, body=payload
        ) from err
    except URLError as err:
        raise AgentWalletApiError(f"Could not reach {base_url}: {err.reason}") from err
