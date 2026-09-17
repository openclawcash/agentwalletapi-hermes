"""Tool handlers for the OpenClawCash Hermes bridge.

Each handler is a thin wrapper over api_client.call_agent_api, mirroring
mcp-server/openclawcash-mcp.mjs. No wallet logic lives here — it lives in
the OpenClawCash agent API, so behavior stays identical across MCP, this
Hermes bridge, and the CLI.

Wallet labels are user-controlled display text: they are returned as data,
never interpreted as instructions, and write actions below select wallets
by walletId, not walletLabel.
"""

from __future__ import annotations

from typing import Any

from .api_client import AgentWalletApiError, call_agent_api

_WALLET_LABEL_RULE = (
    "Wallet label must be 1-32 characters using letters, numbers, spaces, and . _ - ( ) #, "
    "starting with a letter or number, and must not match another wallet's label or a wallet ID."
)


def _selector(arguments: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key in ("walletId", "walletLabel", "walletAddress"):
        if arguments.get(key) is not None:
            out[key] = arguments[key]
    return out


def _error_result(err: AgentWalletApiError) -> dict[str, Any]:
    return {"ok": False, "error": str(err), "status": err.status, "details": err.body}


def agentwalletapi_wallets_list(arguments: dict[str, Any]) -> dict[str, Any]:
    query = {}
    if arguments.get("includeBalances"):
        query["includeBalances"] = "true"
    try:
        return {"ok": True, "wallets": call_agent_api("GET", "/api/agent/wallets", query=query)}
    except AgentWalletApiError as err:
        return _error_result(err)


def agentwalletapi_wallet_get(arguments: dict[str, Any]) -> dict[str, Any]:
    query = {**_selector(arguments)}
    if arguments.get("chain") is not None:
        query["chain"] = arguments["chain"]
    try:
        return {"ok": True, "wallet": call_agent_api("GET", "/api/agent/wallet", query=query)}
    except AgentWalletApiError as err:
        return _error_result(err)


def agentwalletapi_wallet_rename(arguments: dict[str, Any]) -> dict[str, Any]:
    label = arguments.get("label")
    if not isinstance(label, str) or not label.strip():
        return {"ok": False, "error": _WALLET_LABEL_RULE}
    selector = _selector(arguments)
    if not selector:
        return {"ok": False, "error": "Provide exactly one of walletId, walletLabel, or walletAddress."}
    try:
        body = {**selector, "label": label}
        return {"ok": True, "wallet": call_agent_api("PATCH", "/api/agent/wallet", body=body)}
    except AgentWalletApiError as err:
        return _error_result(err)


def agentwalletapi_wallet_create(arguments: dict[str, Any]) -> dict[str, Any]:
    required = ("label", "exportPassphrase", "exportPassphraseStorageType", "exportPassphraseStorageRef")
    missing = [k for k in required if not arguments.get(k)]
    if missing:
        return {"ok": False, "error": f"Missing required field(s): {', '.join(missing)}"}
    if arguments.get("confirmExportPassphraseSaved") is not True:
        return {
            "ok": False,
            "error": "Save exportPassphrase securely first, then set confirmExportPassphraseSaved=true to confirm.",
        }
    body = {
        "label": arguments["label"],
        "exportPassphrase": arguments["exportPassphrase"],
        "exportPassphraseStorageType": arguments["exportPassphraseStorageType"],
        "exportPassphraseStorageRef": arguments["exportPassphraseStorageRef"],
        "confirmExportPassphraseSaved": True,
    }
    if arguments.get("network") is not None:
        body["network"] = arguments["network"]
    try:
        return {"ok": True, "wallet": call_agent_api("POST", "/api/agent/wallets/create", body=body)}
    except AgentWalletApiError as err:
        return _error_result(err)


def agentwalletapi_wallet_import(arguments: dict[str, Any]) -> dict[str, Any]:
    required = ("label", "network", "privateKey")
    missing = [k for k in required if not arguments.get(k)]
    if missing:
        return {"ok": False, "error": f"Missing required field(s): {', '.join(missing)}"}
    body = {k: arguments[k] for k in required}
    try:
        return {"ok": True, "wallet": call_agent_api("POST", "/api/agent/wallets/import", body=body)}
    except AgentWalletApiError as err:
        return _error_result(err)


def agentwalletapi_transfer_send(arguments: dict[str, Any]) -> dict[str, Any]:
    to = arguments.get("to")
    if not to:
        return {"ok": False, "error": "'to' is required."}
    selector = _selector(arguments)
    if not selector:
        return {"ok": False, "error": "Provide exactly one of walletId, walletLabel, or walletAddress."}
    body = {**selector, "to": to}
    for key in ("chain", "network", "amountDisplay", "valueBaseUnits", "token", "memo"):
        if arguments.get(key) is not None:
            body[key] = arguments[key]
    try:
        return {"ok": True, "transfer": call_agent_api("POST", "/api/agent/transfer", body=body)}
    except AgentWalletApiError as err:
        return _error_result(err)
