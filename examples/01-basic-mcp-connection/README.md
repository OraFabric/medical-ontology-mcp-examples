# Example 01 — Basic MCP connection

**Goal:** prove the endpoint, the key and the transport all work, before you touch a
client. Five minutes, no dependencies, no cost.

## Run it

```bash
cp ../../.env.example ../../.env          # then edit in your key
set -a; . ../../.env; set +a

python verify.py
```

Expected output:

```
endpoint         https://orafabric.com/api/dev/mcp
key              set (52 chars, hidden)
handshake        ok  protocol=2024-11-05  session=(none)
tools/list       ok  6 tools
                   check_relation     both_directions filters limit object relation subject
                   explore_concept    concept direction filters limit relations
                   get_coverage       (none)
                   get_paper          id include_findings
                   resolve_concept    limit name type
                   retrieve_evidence  filters include_hypotheses max_evidence query
get_coverage     ok  datasets=25  concepts=23419720  relationships=39268665
                     updated_at=2026-11-06T14:44:11Z
```

What the script actually does, in the order the transport requires:

1. `initialize` with a protocol version and a client name;
2. `notifications/initialized` — a notification, so no `id` and no response body expected;
3. `tools/list`;
4. `tools/call` on `get_coverage`, which is free.

Once this prints, the only things that can still go wrong are on the client side, and
[../../docs/troubleshooting.md](../../docs/troubleshooting.md) covers those.

## Use a client instead

`mcp.json` in this folder is a ready template for clients that read `mcpServers`. Copy it
to the location your client expects — [../../docs/mcp-configuration.md](../../docs/mcp-configuration.md)
lists the exact paths for Claude Desktop, Claude Code, Cursor, VS Code and Continue.

## If it fails

| Output | Meaning |
|---|---|
| `401 invalid_api_key` | prefix doubled, key revoked, or wrong product — see troubleshooting |
| `HTTP 404` | wrong path; it must be `/api/dev/mcp` |
| `cannot reach` | DNS, egress firewall or proxy; try with `env -u http_proxy -u https_proxy` |
| `tools/list returned nothing` | authenticated at transport level but not authorised for tools |

## What to do next

[Example 02](../02-biomedical-research-agent/) — the same connection, now doing a real
research question in several steps.
