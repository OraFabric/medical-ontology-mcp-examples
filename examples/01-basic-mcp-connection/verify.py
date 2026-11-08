#!/usr/bin/env python3
"""Verify that you can reach OraFabric over MCP, with no client and no dependencies.

    export ORAFABRIC_API_KEY=your_api_key_here
    python verify.py

Costs nothing: it only calls the handshake, tools/list and the free get_coverage tool.
Exit code 0 means you are connected.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("ORAFABRIC_MCP_URL", "https://orafabric.com/api/dev/mcp")
TIMEOUT = 60


def post(payload, api_key, session_id=None):
    headers = {
        "Content-Type": "application/json",
        # Both types are required by the Streamable HTTP transport.
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer " + api_key,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8", "replace")
            return response.headers.get("Mcp-Session-Id"), body
    except urllib.error.HTTPError as exc:
        raise SystemExit("HTTP %s from %s\n%s" % (exc.code, ENDPOINT, exc.read().decode("utf-8", "replace")))
    except urllib.error.URLError as exc:
        raise SystemExit("cannot reach %s: %s" % (ENDPOINT, exc.reason))


def parse(body):
    """Accept either a JSON body or a text/event-stream body.

    Events in text/event-stream are separated by blank lines; `event:` is an optional
    field inside one event, so it must not be used as the delimiter. A server that
    sends a progress notification before the result would otherwise have every `data:`
    line joined into one invalid blob.
    """
    body = body.strip()
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass
    events, current = [], []
    for line in body.splitlines():
        if not line.strip():
            if current:
                events.append(current)
                current = []
            continue
        current.append(line)
    if current:
        events.append(current)
    messages = []
    for event in events:
        data = [line[5:].strip() for line in event if line.startswith("data:")]
        if not data:
            continue
        try:
            messages.append(json.loads("\n".join(data)))
        except json.JSONDecodeError:
            continue
    for message in reversed(messages):
        if isinstance(message, dict) and "id" in message and (
            "result" in message or "error" in message
        ):
            return message
    return {}


def main():
    api_key = (os.environ.get("ORAFABRIC_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("set ORAFABRIC_API_KEY first  (see .env.example)")
    # A key pasted from some clients already carries the prefix; strip it to avoid
    # sending "Bearer Bearer ...", which the server rejects with invalid_api_key.
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()

    print("endpoint         %s" % ENDPOINT)
    print("key              set (%d chars, hidden)" % len(api_key))

    session, body = post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "orafabric-verify", "version": "0.1.0"},
            },
        },
        api_key,
    )
    reply = parse(body)
    if not reply:
        raise SystemExit(
            "handshake returned something we could not read as a JSON-RPC message:\n%s"
            % body[:400]
        )
    if "error" in reply:
        raise SystemExit("handshake failed: %s" % reply["error"])
    protocol = reply.get("result", {}).get("protocolVersion", "?")
    print("handshake        ok  protocol=%s  session=%s" % (protocol, session or "(none)"))

    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, api_key, session)

    reply = parse(post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, api_key, session)[1])
    tools = reply.get("result", {}).get("tools", [])
    if not tools:
        raise SystemExit("tools/list returned nothing — check the Authorization header")
    print("tools/list       ok  %d tools" % len(tools))
    for tool in tools:
        props = sorted((tool.get("inputSchema") or {}).get("properties", {}))
        print("                   %-18s %s" % (tool["name"], " ".join(props) or "(none)"))

    reply = parse(
        post(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "get_coverage", "arguments": {}},
            },
            api_key,
            session,
        )[1]
    )
    if "error" in reply:
        raise SystemExit("get_coverage failed: %s" % reply["error"])
    result = reply.get("result", {})
    if result.get("isError"):
        # A failed tool call is HTTP 200 with isError set — not a JSON-RPC error.
        raise SystemExit("get_coverage failed: %s" % json.dumps(result)[:400])
    payload = result.get("structuredContent")
    if not payload:
        for item in result.get("content", []):
            if item.get("type") == "text":
                payload = json.loads(item["text"])
                break
    payload = payload or {}
    print(
        "get_coverage     ok  datasets=%s  concepts=%s  relationships=%s"
        % (len(payload.get("datasets", [])), payload.get("concepts"), payload.get("relationships"))
    )
    print("                     updated_at=%s" % payload.get("updated_at"))
    print("\nconnected. next: docs/quickstart.md")


if __name__ == "__main__":
    sys.exit(main())
