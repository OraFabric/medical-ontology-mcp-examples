"""A minimal OraFabric MCP client — standard library only, no dependencies.

Copy this file into your project and use it as-is, or read it as a reference for the
transport. It implements exactly what the server requires:

    POST initialize                 -> protocolVersion, optional Mcp-Session-Id
    POST notifications/initialized   (notification: no id, expect 202)
    POST tools/list
    POST tools/call

Usage:

    from orafabric_mcp import OraFabricMCP, MCPError

    client = OraFabricMCP()                                  # ORAFABRIC_API_KEY
    client.call("get_coverage")                              # free
    client.call("resolve_concept", {"name": "EGFR"})         # free
    client.call("retrieve_evidence", {"query": "..."})       # $0.03, 11-27 s

Business errors arrive as HTTP 200 with a JSON-RPC error body, and are raised as
MCPError with `.code` set to the server code (`ambiguous_concept`, `insufficient_balance`,
`invalid_api_key`, ...). Branch on `code`, never on the message text.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://orafabric.com/api/dev/mcp"
DEFAULT_TIMEOUT = 180  # retrieval packs have been observed taking 11-27 s

PAID_TOOLS = {"retrieve_evidence", "check_relation", "explore_concept", "get_paper"}


class MCPError(RuntimeError):
    """Transport or server error. `.code` is the server's code when it sent one."""

    def __init__(self, message, code=None, payload=None):
        super().__init__(message)
        self.code = code
        self.payload = payload


class OraFabricMCP:
    def __init__(self, endpoint=None, api_key=None, timeout=DEFAULT_TIMEOUT, max_retries=2):
        self.endpoint = endpoint or os.environ.get("ORAFABRIC_MCP_URL", DEFAULT_ENDPOINT)
        api_key = api_key or os.environ.get("ORAFABRIC_API_KEY", "")
        api_key = api_key.strip()
        # Some configs copy the full header value. Accept both, never send "Bearer Bearer".
        if api_key.lower().startswith("bearer "):
            api_key = api_key[7:].strip()
        if not api_key:
            raise MCPError("ORAFABRIC_API_KEY is not set (see .env.example)")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session_id = None
        self._next_id = 0
        self.protocol_version = None
        self._initialize()

    # ------------------------------------------------------------------ transport

    def _post(self, payload):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + self.api_key,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(
            self.endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self.session_id = session
                return self._decode(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            try:
                error = json.loads(body).get("error", {})
            except (json.JSONDecodeError, AttributeError):
                error = {}
            raise MCPError(
                "HTTP %s: %s" % (exc.code, error.get("message") or body[:300]),
                code=error.get("code"),
                payload=error,
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            raise MCPError("cannot reach %s: %s" % (self.endpoint, getattr(exc, "reason", exc)))

    @staticmethod
    def _decode(body):
        body = body.strip()
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
        # text/event-stream. Events are separated by a blank line, not by the
        # optional `event:` field — a server may send several data-only events
        # in one response. Long calls can be preceded by progress notifications,
        # which are JSON-RPC messages with no `id`; taking the last event blindly
        # would return a notification, and concatenating every data line would
        # produce invalid JSON and silently yield {}.
        fallback, response = {}, {}
        for chunk in re.split(r"\r?\n\r?\n", body):
            data = [ln[5:].strip() for ln in chunk.splitlines() if ln.startswith("data:")]
            if not data:
                continue
            try:
                parsed = json.loads("\n".join(data))
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and ("result" in parsed or "error" in parsed):
                response = parsed
            elif not fallback:
                fallback = parsed
        return response or fallback

    def _request(self, method, params=None):
        self._next_id += 1
        reply = self._post(
            {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        )
        if "error" in reply:
            error = reply["error"]
            raise MCPError(
                "MCP error %s: %s" % (error.get("code"), error.get("message")),
                code=error.get("code"),
                payload=error,
            )
        return reply.get("result", {})

    def _notify(self, method, params=None):
        self._post({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _initialize(self):
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "orafabric-examples", "version": "0.1.0"},
            },
        )
        self.protocol_version = result.get("protocolVersion")
        self._notify("notifications/initialized")

    # ------------------------------------------------------------------------ api

    def list_tools(self):
        return self._request("tools/list").get("tools", [])

    def call(self, name, arguments=None, retries=None):
        """Call one tool and return the parsed payload.

        Retries only on transport failures, never on a business error: repeating an
        `insufficient_balance` or `ambiguous_concept` call cannot help and costs money.
        """
        if retries is None:
            retries = self.max_retries
        attempt = 0
        while True:
            try:
                result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
                break
            except MCPError as exc:
                if exc.code or attempt >= retries:
                    raise
                attempt += 1
                time.sleep(1.5 * attempt)

        if result.get("isError"):
            raise MCPError("tool %s reported an error: %s" % (name, result))

        structured = result.get("structuredContent")
        if structured:
            return structured
        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    return json.loads(item["text"])
                except (json.JSONDecodeError, KeyError):
                    return {"text": item.get("text", "")}
        return result

    # -------------------------------------------------------------------- helpers

    @staticmethod
    def field(item, *names, default=None):
        """Read the first present key. Finding keys vary slightly between dataset
        versions, so never hard-code one name in your rendering code."""
        if not isinstance(item, dict):
            return default
        for name in names:
            value = item.get(name)
            if value not in (None, "", [], {}):
                return value
        return default

    @classmethod
    def claim(cls, finding):
        return cls.field(finding, "claim", "statement", "finding", "text", default="")

    @classmethod
    def sentence(cls, finding):
        """The quote. Real packs carry it under the bare key `evidence` — which reads
        like a flag and is actually the sentence. Check it before you trust a UI."""
        return cls.field(finding, "evidence", "source_sentence", "sentence", "quote",
                         "evidence_sentence", default="")

    @classmethod
    def strength(cls, finding):
        return cls.field(finding, "evidence_strength", "strength", "strongest_evidence_strength", default="")

    @classmethod
    def design(cls, finding):
        """Study design lives inside `evidence_strength_basis`, a dict, not in a flat key."""
        basis = finding.get("evidence_strength_basis") if isinstance(finding, dict) else None
        if isinstance(basis, dict):
            value = cls.field(basis, "study_design", "design", "study_type", default="")
            if value:
                return value
        return cls.field(finding, "study_type", "study_design", "design", default="")

    @classmethod
    def paper_ref(cls, finding):
        """A paper id (string). Metadata is a separate, paid `get_paper` call."""
        return cls.field(finding, "paper_id", "paper", "paper_ref", "source_paper", default=None)

    @staticmethod
    def mentions_both(text, first, second):
        """The free quality gate for two-entity questions: does the claim actually
        connect both endpoints? See docs/evidence-semantics.md."""
        text = (text or "").lower()
        return first.lower() in text and second.lower() in text
