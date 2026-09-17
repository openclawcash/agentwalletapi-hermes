"""Hermes bridge for OpenClawCash managed wallets.

Covers core wallet management (list, get, rename, create, import, transfer)
— the same operations exposed by the OpenClawCash MCP server's wallet tool
set. It is not full parity with all MCP server tools (swap, bridge, Get
Paid checkout, Polymarket, YieldWolf Casino): add those the same way, one
schema in schemas.py, one thin handler in tools.py, one register_tool call
below.
"""

from . import schemas, tools


def register(ctx):
    for schema, handler in (
        (schemas.WALLETS_LIST, tools.agentwalletapi_wallets_list),
        (schemas.WALLET_GET, tools.agentwalletapi_wallet_get),
        (schemas.WALLET_RENAME, tools.agentwalletapi_wallet_rename),
        (schemas.WALLET_CREATE, tools.agentwalletapi_wallet_create),
        (schemas.WALLET_IMPORT, tools.agentwalletapi_wallet_import),
        (schemas.TRANSFER_SEND, tools.agentwalletapi_transfer_send),
    ):
        ctx.register_tool(
            name=schema["name"],
            toolset="agentwalletapi",
            schema=schema,
            handler=handler,
            description=schema["description"],
        )
