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
    client.call("retrieve_evidence", {"query": "..."})       # $0.03, 11-50 s

Business errors arrive in two shapes, and both end up as the same `MCPError`:

    HTTP 401 with a JSON-RPC `error` object        (invalid_api_key, bad header)
    HTTP 200 with `result.isError` + `structuredContent.error`
                                                   (insufficient_balance, ambiguous_concept)

Either way `.code` carries the server code. Branch on `code`, never on the message text.
"""

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://orafabric.com/api/dev/mcp"
DEFAULT_TIMEOUT = 180  # retrieval packs have been observed taking 11-50 s

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
    def _events(body):
        """Split a text/event-stream body into events.

        SSE frames are separated by **blank lines**, not by `event:` lines — `event:`
        is an optional field inside a frame. Splitting on `event:` breaks the moment a
        server sends a notification (progress, logging) ahead of the result without
        labelling it, because every `data:` line in the body then gets concatenated
        into one invalid JSON blob.
        """
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
        return events

    @classmethod
    def _decode(cls, body):
        """Return the JSON-RPC response for our request.

        Prefer the last frame that actually carries an id and a result or error; skip
        notifications (no id) and anything that does not parse.
        """
        body = body.strip()
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
        messages = []
        for event in cls._events(body):
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

    def _request(self, method, params=None):
        self._next_id += 1
        reply = self._post(
            {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        )
        if not reply:
            # Never hand back an empty dict: a response we could not read is a
            # transport failure, and the caller must not treat it as "no data".
            raise MCPError("no JSON-RPC response in the body returned by %s" % self.endpoint)
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
            error = self._business_error(result)
            raise MCPError(
                error.get("message") or "tool %s reported an error" % name,
                code=error.get("code"),
                payload=error or result,
            )

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
    def _business_error(result):
        """Pull `{code, message}` out of a failed tool call.

        A failed call is still HTTP 200 and still a JSON-RPC *result*: the error sits in
        `structuredContent.error`, or in the first `content[].text` as JSON. Callers are
        told to branch on `code`, so the code has to survive the trip.
        """
        structured = result.get("structuredContent")
        if isinstance(structured, dict) and isinstance(structured.get("error"), dict):
            return structured["error"]
        for item in result.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    parsed = json.loads(item.get("text") or "")
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
                    return parsed["error"]
        return {}

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
