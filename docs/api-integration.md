# Integrating OraFabric into an application

There is no separate REST API to learn. **MCP is the API.** The same six tools your
assistant uses in Claude or Cursor are callable from your Python service with the same
arguments and the same responses.

This page is about wiring it in properly: how to structure calls, what to cache, what to
show, and where the failure modes are.

---

## 1. Copy one file

`examples/04-python-api-integration/orafabric_mcp.py` — standard library only, no
dependencies, ~130 lines. It handles the handshake, the `Accept` header, SSE or JSON
responses, session ids and errors.

```python
from orafabric_mcp import OraFabricMCP

client = OraFabricMCP()                       # reads ORAFABRIC_API_KEY
coverage = client.call("get_coverage")        # free
node = client.call("resolve_concept", {"name": "KRAS G12C", "limit": 3})
pack = client.call("retrieve_evidence", {     # $0.03, 11-50 s
    "query": "KRAS G12C inhibitor resistance mechanisms in non-small cell lung cancer"
})
```

Two behaviours from the client worth knowing:

- `call()` returns the parsed payload directly (`structuredContent` when present, otherwise
  the decoded text content), so you never unwrap `content[0].text` yourself.
- business errors are raised as `MCPError` carrying the server's `code` — `ambiguous_concept`,
  `insufficient_balance`, `invalid_api_key`. Branch on the code, never on the message text.

---

## 2. A call pattern that survives contact with users

```
question
  └─ get_coverage            (free)   is this topic even in scope?
  └─ resolve_concept         (free)   pin the names to ids; catch ambiguity here
  └─ retrieve_evidence       ($0.03)  one call, phrased like a paper sentence
  └─ filter: both endpoints mentioned, [incidental] tagged
  └─ get_paper               ($0.03 each) only for papers you will display
  └─ your LLM                writes prose, with source sentences attached
```

Anti-patterns that look reasonable and are not:

- **Retrying a paid call to get more.** More calls do not add recall; a rewritten query
  does. The rewrite is free.
- **Calling `check_relation` as an existence check.** It returns evidence buckets, not a
  verdict. If your feature is "is A related to B", render the evidence and let the user
  judge, or use `retrieve_evidence` with a question that names both.
- **Feeding the model the whole 60-finding pack.** Rank first, pass the top handful with
  source sentences, and let the model cite. A context window full of unrelated findings
  produces confident nonsense.
- **Parallel paid calls in one request.** Serialize them. Observed behaviour under
  concurrency is dropped connections, not queued work.

---

## 3. Caching and cost

| Layer | TTL | Why |
|---|---|---|
| `get_coverage` | one per process start | free, and the counts change slowly |
| `resolve_concept` result | long (per name) | node ids are stable; names are not |
| evidence pack | 1–24 h, keyed by normalised query | the graph updates on a schedule |
| `get_paper` | long (per paper id) | paper metadata does not change |

Normalise the cache key aggressively: lowercase, collapse whitespace, strip trailing
punctuation. Two queries that differ only in a stop word should hit the same entry.

Budget for a single-question product flow: **$0.03–$0.09**. Budget for a chat product
with a retrieval panel: $0.03 per turn, and cache hard.

---

## 4. Timeouts, and telling the user something is happening

Retrieval takes 11–50 s. In a synchronous handler that is a timeout waiting to happen, so:

- set the HTTP timeout to **120–180 s**, not the library default;
- stream progress ("retrieving evidence…", "reading 4 papers…") or push it into a job
  queue and poll;
- never hold a database transaction open across a paid call.

If your platform caps request duration (many serverless platforms cap at 10–30 s), move
the call to a worker. This is the most common integration failure we see, and it is
entirely on the client side.

---

## 5. What to put in the prompt

The model is not the evidence layer. Keep them separate:

```
You are given findings retrieved from a biomedical knowledge graph.
For every statement you make, cite the finding id it came from.
Use only the retrieved findings; if they do not support an answer, say so.
Keep observed results, associations, author interpretations and hypotheses
distinct and label each one.
Do not convert a non-empty evidence bucket into a causal claim.
End with what the evidence does not cover.
```

The full prompt pack is in
`examples/02-biomedical-research-agent/prompts.md` and
`examples/03-evidence-based-reasoning/prompts.md`.

---

## 6. Multi-tenant SaaS notes

- **One key per tenant or per environment.** Never share a production key with a demo app;
  billing attribution and revocation both become impossible.
- **Store the key in a secret manager**, not in a database column you also log.
- **Log the tool name, the argument hash and the call cost — never the key, and never a
  full pack** (packs contain licensed article sentences). Log ids and counts.
- **Surface `insufficient_balance` as a product state**, not a 500. Your customer needs to
  top up (new accounts start with $3.00, ≈100 calls), and a raw error will lose them.

---

## 7. Health-tech specific

This is a research and literature layer. If you are building anything a clinician might
act on:

- show the source sentence next to every claim, always;
- label single-study evidence as single-study;
- keep a "not medical advice" boundary in the UI, not only in the terms;
- log which finding ids were shown for which answer, so a review is possible later.

Regulatory review of an AI medical product will ask how a claim was sourced. If you
cannot answer that at the level of "this sentence, this paper, this design", the integration
is not finished.
