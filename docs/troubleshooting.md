# Troubleshooting

Every item here is an error we have actually hit while integrating, with the cause we
found. Start with `python examples/01-basic-mcp-connection/verify.py` — it isolates
transport from client.

---

## `401 invalid_api_key`

```json
{"error": {"code": "invalid_api_key", "message": "Invalid MCP API key"}}
```

Three causes, in order of frequency:

1. **A doubled `Bearer`.** The value copied from the console sometimes already looks like
   `Bearer ora_live_…`, and client configs then prepend `Bearer ` again, producing
   `Authorization: Bearer Bearer ora_live_…`. Fix: put the raw key in the config and let
   the `Bearer ` prefix come from the header template, or strip the prefix in code.
2. **A revoked or rotated key.** Keys issued earlier stop working silently. The console
   shows the key's state.
3. **The key from a different product** (a sandbox or a different tenant).

The client in `examples/04` strips a leading `Bearer ` defensively for this reason.

## `402` / `insufficient_balance`

It comes back **HTTP 200**, not 402 — a failed tool call is still a JSON-RPC *result*:

```json
{"jsonrpc": "2.0", "id": 7, "result": {
  "content": [{"type": "text", "text": "{\"error\": {\"code\": \"insufficient_balance\", \"message\": \"...\"}}"}],
  "isError": true,
  "structuredContent": {"error": {"code": "insufficient_balance",
   "message": "Your balance is too low to complete this call. Top up at https://orafabric.com/dev/topup"}}}}
```

`invalid_api_key` is different: that one is a real JSON-RPC `error` on HTTP 401. The
client in `examples/04` turns both into `MCPError` with `.code` set, so application code
only ever branches on the code.

Only paid tools return this; `get_coverage` and `resolve_concept` keep working, which is
why the quickstart uses them.

New accounts start with **$3.00 (≈100 paid calls)**, so seeing this means the credit is
used up — not that the integration is broken. Check the console balance before debugging
anything else. Handle it in your product as a normal state (banner + top-up link
<https://orafabric.com/dev/topup>), never as a 500.

## Works in `curl`, fails in my client

Check the `Accept` header. Streamable HTTP MCP requires both:

```
Accept: application/json, text/event-stream
```

Omit `text/event-stream` and some intermediaries answer `406`, or the server streams an
event body your client cannot read, which looks like an empty response. If a response
arrives as `text/event-stream`, read the `data:` lines and parse the last JSON object that
carries `result` or `error`.

## `initialize` succeeds, `tools/list` returns nothing

The request was authenticated at the transport level but not authorised for tools — usually
a key with a narrower scope, or a proxy rewriting headers. Compare the exact header bytes
with `verify.py`.

## `RemoteDisconnected` / truncated response / timeouts

Not a server-side crash. In our environment this was always the **client's egress proxy**:

- the proxy caps request duration below the 11–50 s a retrieval pack needs;
- parallel paid calls get dropped rather than queued.

Diagnosis: run `verify.py` with the proxy variables removed, and run the paid call alone.

```bash
env -u http_proxy -u https_proxy -u ALL_PROXY python examples/01-basic-mcp-connection/verify.py
```

If serial + no-proxy works, the workaround is on your side: raise the timeout, serialize
paid calls, and move long calls to a worker.

## `ambiguous_concept`

```json
{"error": {"code": "ambiguous_concept",
 "message": "A name matches several concepts: Metformin, Metformin"}}
```

The name maps to more than one node. **You are not billed for this call.** Fix:

```python
client.call("resolve_concept", {"name": "metformin", "limit": 10})   # see the candidates
client.call("check_relation", {
    "subject": "Metformin (AMPK activator) treatment",               # disambiguate the phrase
    "object": "immune checkpoint inhibitor therapy",
})
```

Bare drug names are the usual trigger. Use the fuller label from `resolve_concept`.

## A paid tool returns an empty pack

Before you call it a bug:

1. `get_coverage` — is the topic inside the listed datasets? The graph is oncology-first.
2. Rewrite the query as a sentence an author would write. Four stacked technical terms
   often return zero for a well-covered topic.
3. `resolve_concept` the anchor names — an unmatched subject silently narrows the query.
4. Try `explore_concept` on the anchor instead; if the neighbourhood is populated, the
   graph has the entity and the question is the problem.

If all four pass and it is still empty, open an issue with the exact query. Empty results
are coverage statements and we want to know about them.

## `papers` at the top level of a pack is `[]`

Observed in every response so far. Paper metadata for a finding comes from the reference
attached to that finding, or from `get_paper` with the id. Do not build a UI that depends
on the top-level array being populated.

## `explore_concept` crashes while sorting

`strongest_evidence_strength` can be `null`. Sort null-safe:

```python
rank = {"high": 3, "moderate": 2, "low": 1, "very_low": 0}
key = lambda n: rank.get(n.get("strongest_evidence_strength") or "", -1)
```

## `check_relation` returned findings that are off-topic

Expected. The buckets are evidence around the subject and object, not a validated edge.
Filter for findings whose claim mentions **both** endpoints before showing anything. See
[evidence-semantics.md](evidence-semantics.md#4-the-endpoint-test--a-free-quality-gate).

## My client shows 20 tools, not 6

You have another MCP server configured in the same client; the tool lists are merged.
Name-qualify your calls (`orafabric.retrieve_evidence` in Claude, or the server prefix your
client uses) to avoid a same-named tool from another server answering.

## `404` on the endpoint

The path is `/api/dev/mcp`. A bare host, `/mcp`, or `/sse` will 404. Copy the URL exactly.

---

## Still stuck

Open an issue with:

- the output of `verify.py` (it redacts the key),
- your client and version,
- the tool name and the arguments you passed,
- the full error body, with the key removed.

Do not paste a working config file into an issue — it contains your key.
