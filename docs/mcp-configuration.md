# MCP configuration

One endpoint, one header. Everything on this page is the same server with a different
config file around it.

```json
{
  "mcpServers": {
    "orafabric": {
      "url": "https://orafabric.com/api/dev/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

| Setting | Value |
|---|---|
| Transport | Streamable HTTP (JSON-RPC 2.0 over POST) |
| Endpoint | `https://orafabric.com/api/dev/mcp` |
| Auth header | `Authorization: Bearer <key>` |
| Session id | Not required by this server; if a response returns `Mcp-Session-Id`, echo it on later requests |
| Protocol version | The server currently reports `2024-11-05` during the handshake, whatever version the client proposes. Accept it rather than asserting a version |
| Required `Accept` header | `application/json, text/event-stream` |
| Recommended timeout | 120–180 s |

The developer console at <https://orafabric.com> copies a complete configuration for you.
Use it when possible: it produces a correctly formed `Authorization` value, which is where
most hand-edited configs break.

---

## Claude Desktop

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "orafabric": {
      "url": "https://orafabric.com/api/dev/mcp",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

Quit and reopen the app — reloading the window is not enough. Then check the tools
indicator; if the server shows as connected you should see six tools.

## Claude Code

```bash
claude mcp add --transport http orafabric https://orafabric.com/api/dev/mcp \
  --header "Authorization: Bearer $ORAFABRIC_API_KEY"
claude mcp list
```

To check it from a script rather than a session, run the same request the CLI sends:

```bash
curl -sS https://orafabric.com/api/dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $ORAFABRIC_API_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -c 600
```

## Cursor

`~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project):

```json
{
  "mcpServers": {
    "orafabric": {
      "url": "https://orafabric.com/api/dev/mcp",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

## VS Code

`.vscode/mcp.json` — note that VS Code uses `servers`, not `mcpServers`:

```json
{
  "servers": {
    "orafabric": {
      "type": "http",
      "url": "https://orafabric.com/api/dev/mcp",
      "headers": { "Authorization": "Bearer ${input:orafabric-key}" }
    }
  },
  "inputs": [
    {
      "id": "orafabric-key",
      "type": "promptString",
      "description": "OraFabric API key",
      "password": true
    }
  ]
}
```

The `inputs` block keeps the key out of the file, which is the right habit for a
repository that might get committed.

## Continue

`~/.continue/config.yaml`:

```yaml
mcpServers:
  - name: orafabric
    type: streamable-http
    url: https://orafabric.com/api/dev/mcp
    headers:
      Authorization: Bearer ${{ secrets.ORAFABRIC_API_KEY }}
```

## Anything else that speaks Streamable HTTP MCP

No SDK is required. The whole protocol surface this server needs is:

```
POST initialize                 -> read the returned protocolVersion and any Mcp-Session-Id
POST notifications/initialized   (notification: no id, expect 202)
POST tools/list                  -> six tools with inputSchema
POST tools/call                  -> {"name": "...", "arguments": {...}}
```

`examples/01-basic-mcp-connection/verify.py` and
`examples/04-python-api-integration/orafabric_mcp.py` implement exactly that in the
standard library, in about 120 lines. If your framework wants a reference client, use one
of those.

## If you are behind a proxy

The client inherits `http_proxy` / `https_proxy` from the environment. Two things go wrong
in ways that look like server failures:

- a proxy that caps request duration below the 11–50 s a retrieval pack can take, which
  surfaces as a truncated connection or `RemoteDisconnected`;
- parallel paid calls through the same proxy, which get dropped rather than queued.

Fix by raising your own client/proxy timeout and calling tools **serially**:

```bash
env -u http_proxy -u https_proxy -u ALL_PROXY python examples/01-basic-mcp-connection/verify.py
```

If serial calls succeed and parallel ones fail, the bottleneck is on your side. Report
that in an issue and we will help you measure it rather than guess.

## Keeping the key out of the repo

`.gitignore` already excludes `.env` and `*.local.json`. Use `.env.example` as the
template:

```bash
cp .env.example .env
$EDITOR .env      # paste the key
set -a; . ./.env; set +a
```

Never commit a working config copied from the console: those files contain the key
itself. GitHub's secret scanning is a net, not a plan.
