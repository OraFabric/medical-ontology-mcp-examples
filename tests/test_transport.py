"""Transport tests that need no network and no API key.

Run:  python -m unittest discover -s tests -v

The point of these is narrow and deliberate: the two parsers in this repository must
behave identically on every stream shape a Streamable-HTTP MCP server is allowed to
return, including the ones that only appear once a server starts sending progress
notifications. A parser that quietly returns {} on an unreadable body is worse than one
that raises, because the caller renders an empty answer instead of a failure.
"""

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(relative_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load("examples/01-basic-mcp-connection/verify.py", "verify_under_test")
client_mod = load("examples/04-python-api-integration/orafabric_mcp.py", "client_under_test")

RESULT = {"jsonrpc": "2.0", "id": 1, "result": {"ok": 1}}
NOTIFY = {"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 10}}


def brief(message):
    """What the caller will actually read: the result payload, or the error object."""
    if not isinstance(message, dict) or not message:
        return {}
    if "error" in message:
        return {"error": message["error"]}
    return message.get("result", {})


SHAPES = {
    "plain json body": json.dumps(RESULT),
    "single event with event:": "event: message\ndata: %s\n\n" % json.dumps(RESULT),
    "single event without event:": "data: %s\n\n" % json.dumps(RESULT),
    "progress then result, no event:": "data: %s\n\ndata: %s\n\n" % (json.dumps(NOTIFY), json.dumps(RESULT)),
    "progress then result, with event:": (
        "event: message\ndata: %s\n\nevent: message\ndata: %s\n\n" % (json.dumps(NOTIFY), json.dumps(RESULT))
    ),
    "result then notification": "data: %s\n\ndata: %s\n\n" % (json.dumps(RESULT), json.dumps(NOTIFY)),
    "crlf framing": "event: message\r\ndata: %s\r\n\r\nevent: message\r\ndata: %s\r\n\r\n"
    % (json.dumps(NOTIFY), json.dumps(RESULT)),
    "multi-line data in one event": 'data: {"jsonrpc": "2.0",\ndata: "id": 1, "result": {"ok": 1}}\n\n',
    "keepalive comment first": ": ping\n\ndata: %s\n\n" % json.dumps(RESULT),
    "notification only": "data: %s\n\n" % json.dumps(NOTIFY),
    "empty body": "",
}


EXPECTED = {name: {"ok": 1} for name in SHAPES if name not in ("notification only", "empty body")}
EXPECTED["notification only"] = {}
EXPECTED["empty body"] = {}


class TestStreamShapes(unittest.TestCase):
    def test_verify_parser_agrees_on_every_shape(self):
        for name, body in SHAPES.items():
            with self.subTest(shape=name):
                self.assertEqual(brief(verify.parse(body)), EXPECTED[name])

    def test_client_decoder_agrees_on_every_shape(self):
        for name, body in SHAPES.items():
            with self.subTest(shape=name):
                self.assertEqual(brief(client_mod.OraFabricMCP._decode(body)), EXPECTED[name])

    def test_both_parsers_agree(self):
        for name, body in SHAPES.items():
            with self.subTest(shape=name):
                self.assertEqual(
                    brief(verify.parse(body)),
                    brief(client_mod.OraFabricMCP._decode(body)),
                )


def offline_client():
    """A client with no constructor call, so nothing touches the network."""
    client = object.__new__(client_mod.OraFabricMCP)
    client.endpoint = "https://example.invalid/mcp"
    client.max_retries = 0
    client._next_id = 0
    return client


class TestFailureIsLoud(unittest.TestCase):
    def test_unreadable_body_raises_instead_of_returning_empty_dict(self):
        client = offline_client()
        client._post = lambda payload: {}
        with self.assertRaises(client_mod.MCPError):
            client._request("tools/list")

    def test_business_error_keeps_its_code(self):
        failed = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [{"type": "text", "text": '{"error": {"code": "insufficient_balance"}}'}],
                "isError": True,
                "structuredContent": {
                    "error": {"code": "insufficient_balance", "message": "Your balance is too low"}
                },
            },
        }
        client = offline_client()
        client._request = lambda method, params=None: failed["result"]
        with self.assertRaises(client_mod.MCPError) as caught:
            client.call("retrieve_evidence", {"query": "anything"})
        self.assertEqual(caught.exception.code, "insufficient_balance")

    def test_business_error_from_text_content_keeps_its_code(self):
        failed = {
            "content": [{"type": "text", "text": '{"error": {"code": "ambiguous_concept"}}'}],
            "isError": True,
        }
        client = offline_client()
        client._request = lambda method, params=None: failed
        with self.assertRaises(client_mod.MCPError) as caught:
            client.call("check_relation", {"subject": "a", "object": "b"})
        self.assertEqual(caught.exception.code, "ambiguous_concept")


if __name__ == "__main__":
    unittest.main()
