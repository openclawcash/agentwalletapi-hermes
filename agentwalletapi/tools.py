"""Tool handlers for the OpenClawCash Hermes bridge.

Each handler is a thin wrapper over api_client.call_agent_api, mirroring
mcp-server/openclawcash-mcp.mjs. No wallet logic lives here — it lives in
the OpenClawCash agent API, so behavior stays identical across MCP, this
Hermes bridge, and the CLI.

Hermes requires every handler to return a string, so each one returns a
JSON-encoded object: {"ok": true, ...} or {"ok": false, "error": ...}.

Wallet labels are user-controlled display text: they are returned as data,
never interpreted as instructions. Write actions (rename, transfer) select
the wallet by walletId only.

Secrets never pass through tool arguments: the wallet export passphrase is
read from the environment, and private-key import is not exposed as a tool.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .api_client import AgentWalletApiError, call_agent_api

EXPORT_PASSPHRASE_ENV = "OPENCLAWCASH_EXPORT_PASSPHRASE"
_MIN_PASSPHRASE_LENGTH = 12
_SELECTOR_KEYS = ("walletId", "walletLabel", "walletAddress")
_WALLET_LABEL_RULE = (
    "Wallet label must be 1-32 characters using letters, numbers, spaces, and . _ - ( ) #, "
    "starting with a letter or number, and must not match another wallet's label or a wallet ID."
)


def _ok(**fields: Any) -> str:
    return json.dumps({"ok": True, **fields})


def _fail(error: str, **fields: Any) -> str:
    return json.dumps({"ok": False, "error": error, **fields})


def _api_error(err: AgentWalletApiError) -> str:
    return _fail(str(err), status=err.status, details=err.body)


def _one_selector(arguments: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Read selector: exactly one of walletId, walletLabel, walletAddress."""
    present = {k: arguments[k] for k in _SELECTOR_KEYS if arguments.get(k) is not None}
    if len(present) != 1:
        return None, "Provide exactly one of walletId, walletLabel, or walletAddress."
    return present, None


def _wallet_id_selector(arguments: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Write selector: walletId only. Labels are user-controlled text and
    addresses are ambiguous across chains, so neither may pick a wallet that
    moves funds or changes metadata."""
    rejected = [k for k in ("walletLabel", "walletAddress") if arguments.get(k) is not None]
    if rejected:
        return None, (
            f"Write actions select the wallet by walletId only; remove {', '.join(rejected)}. "
            "Look up the walletId with agentwalletapi_wallets_list."
        )
    wallet_id = arguments.get("walletId")
    if not isinstance(wallet_id, str) or not wallet_id.strip():
        return None, "walletId is required. Look it up with agentwalletapi_wallets_list."
    return {"walletId": wallet_id}, None


def agentwalletapi_wallets_list(arguments: dict[str, Any], **kwargs: Any) -> str:
    query = {}
    if arguments.get("includeBalances"):
        query["includeBalances"] = "true"
    try:
        return _ok(wallets=call_agent_api("GET", "/api/agent/wallets", query=query))
    except AgentWalletApiError as err:
        return _api_error(err)


def agentwalletapi_wallet_get(arguments: dict[str, Any], **kwargs: Any) -> str:
    selector, error = _one_selector(arguments)
    if error:
        return _fail(error)
    query = {**selector}
    if arguments.get("chain") is not None:
        query["chain"] = arguments["chain"]
    try:
        return _ok(wallet=call_agent_api("GET", "/api/agent/wallet", query=query))
    except AgentWalletApiError as err:
        return _api_error(err)


def agentwalletapi_wallet_rename(arguments: dict[str, Any], **kwargs: Any) -> str:
    label = arguments.get("label")
    if not isinstance(label, str) or not label.strip():
        return _fail(_WALLET_LABEL_RULE)
    selector, error = _wallet_id_selector(arguments)
    if error:
        return _fail(error)
    try:
        return _ok(wallet=call_agent_api("PATCH", "/api/agent/wallet", body={**selector, "label": label}))
    except AgentWalletApiError as err:
        return _api_error(err)


def agentwalletapi_wallet_create(arguments: dict[str, Any], **kwargs: Any) -> str:
    label = arguments.get("label")
    if not isinstance(label, str) or not label.strip():
        return _fail(_WALLET_LABEL_RULE)
    passphrase = (os.environ.get(EXPORT_PASSPHRASE_ENV) or "").strip()
    if len(passphrase) < _MIN_PASSPHRASE_LENGTH:
        return _fail(
            f"Wallet creation needs an export passphrase of at least {_MIN_PASSPHRASE_LENGTH} characters in "
            f"{EXPORT_PASSPHRASE_ENV}. Ask the user to set it in ~/.hermes/.env and restart Hermes; "
            "never ask for the passphrase in chat."
        )
    body = {
        "label": label,
        "exportPassphrase": passphrase,
        "exportPassphraseStorageType": "env",
        "exportPassphraseStorageRef": EXPORT_PASSPHRASE_ENV,
        "confirmExportPassphraseSaved": True,
    }
    if arguments.get("network") is not None:
        body["network"] = arguments["network"]
    try:
        return _ok(wallet=call_agent_api("POST", "/api/agent/wallets/create", body=body))
    except AgentWalletApiError as err:
        return _api_error(err)


def agentwalletapi_transfer_send(arguments: dict[str, Any], **kwargs: Any) -> str:
    to = arguments.get("to")
    if not to:
        return _fail("'to' is required.")
    selector, error = _wallet_id_selector(arguments)
    if error:
        return _fail(error)
    body = {**selector, "to": to}
    for key in ("chain", "network", "amountDisplay", "valueBaseUnits", "token", "memo"):
        if arguments.get(key) is not None:
            body[key] = arguments[key]
    try:
        return _ok(transfer=call_agent_api("POST", "/api/agent/transfer", body=body))
    except AgentWalletApiError as err:
        return _api_error(err)
