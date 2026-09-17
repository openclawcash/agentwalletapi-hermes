# OpenClawCash — Hermes Agent plugin

Managed EVM and Solana wallets for AI agents, as native Hermes tools.

This plugin is a thin, stateless bridge to the [OpenClawCash agent API](https://openclawcash.com/mcp) — the
same API behind the OpenClawCash MCP server and CLI — so wallet behavior is identical across every surface.
No wallet logic, key material, or fund movement lives in the plugin.

## Requirements

- Hermes Agent with the plugin system
- An OpenClawCash agent key — create one at [openclawcash.com](https://openclawcash.com)

## Install

From this repository (installs as a custom source and can be pinned to an exact commit):

```bash
hermes plugins install openclawcash/agentwalletapi-hermes --enable

# pinned to a reviewed commit
hermes plugins install openclawcash/agentwalletapi-hermes --ref <40-character-commit-sha> --enable
```

Manual install — copy the `agentwalletapi/` directory into your Hermes plugins directory
(`~/.hermes/plugins/`, or `<profile>/plugins/` for a named profile), then:

```bash
hermes plugins enable agentwalletapi
```

Provide the agent key as an environment variable (keep secrets in `~/.hermes/.env`):

```bash
OPENCLAWCASH_AGENT_KEY=occ_your_api_key
```

## Tools

| Tool | What it does |
|---|---|
| `agentwalletapi_wallets_list` | List the managed wallets available to the configured agent key. Optional `includeBalances`. |
| `agentwalletapi_wallet_get` | Fetch one wallet with native and token balances. |
| `agentwalletapi_wallet_rename` | Update a wallet's label. Metadata only — no funds move. |
| `agentwalletapi_wallet_create` | Create a new managed wallet. Requires an export passphrase you have stored yourself plus an explicit confirmation that it is saved. |
| `agentwalletapi_wallet_import` | Import an existing wallet from a private key. |
| `agentwalletapi_transfer_send` | Send a native asset or token transfer from a managed wallet. |

`wallet_get`, `wallet_rename`, and `transfer_send` select the wallet with exactly one of `walletId`,
`walletLabel`, or `walletAddress` (`walletId` preferred). Networks: `sepolia`, `mainnet`,
`polygon-mainnet`, `base-mainnet`, `solana-devnet`, `solana-testnet`, `solana-mainnet`.

## Configuration

| Variable | Fallback | Default | Purpose |
|---|---|---|---|
| `OPENCLAWCASH_AGENT_KEY` | `AGENTWALLETAPI_KEY` | — | Authenticates every request (sent as `X-Agent-Key`). |
| `OPENCLAWCASH_BASE_URL` | `AGENTWALLETAPI_URL` | `https://openclawcash.com` | API host. |

## Security

- **Host allowlist.** The base URL is read from the environment, so a tampered value could redirect the
  agent key to an attacker-controlled host. Only `https://openclawcash.com` or
  `https://<subdomain>.openclawcash.com` is accepted — no port, path, or embedded credentials — and any
  other value is refused before a request is made.
- **Key handling.** The agent key travels only in the `X-Agent-Key` header to that allowlisted host. It is
  never logged and never returned in tool output.
- **Write tools expect approval.** `wallet_create`, `wallet_import`, and `transfer_send` are declared
  high-risk and are meant to run under Hermes session approval mode.
- **Labels are data, not instructions.** Wallet labels are user-controlled text; they are returned as data
  and never interpreted as instructions, and write actions select wallets by `walletId`.

## Scope

Core wallet management only. Not yet covered: swap, bridge, Get Paid checkout, Polymarket, and YieldWolf
Casino tools. Adding one follows the same pattern — a schema in `agentwalletapi/schemas.py`, a thin handler
in `agentwalletapi/tools.py`, and one `register_tool` line in `agentwalletapi/__init__.py`.

## License

MIT — see [LICENSE](LICENSE).

"OpenClawCash" is a trademark of OpenClawCash; forks must not imply endorsement.

## Links

- Agent API and MCP server: <https://openclawcash.com/mcp>
- Issues and requests: <https://github.com/openclawcash/agentwalletapi-hermes/issues>
