# Quickstart

Zero to a real answer, in the order a developer actually does it.

There are two paths here. Pick one.

- **Path A — you have an MCP client.** Five minutes, no code.
- **Path B — you are building the client.** Ten minutes, one Python file.

---

## 0. The endpoint

```
https://orafabric.com/api/dev/mcp
```

Streamable HTTP, JSON-RPC 2.0. Authentication is a bearer token in the `Authorization`
header. Every request after the handshake carries it; no session id is required by this
server (it may return one — if it does, echo it back).

```bash
export ORAFABRIC_MCP_URL=https://orafabric.com/api/dev/mcp
export ORAFABRIC_API_KEY=your_api_key_here
```

Get a key at <https://orafabric.com/dev/login?next=/dev>. Registration and login are the
same page, and **new accounts start with $3.00 of credit — about 100 paid calls**, which
covers every example in this repository.

Press **Copy** in the console: it copies a complete, ready-to-paste MCP configuration,
key included. Prefer it over hand-editing — hand-editing is where the doubled `Bearer`
prefix happens (see [troubleshooting](troubleshooting.md#401-invalid_api_key)).

---

## Path A — an MCP client

### A1. Claude Desktop

Edit the config file and restart the app:

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

### A2. Claude Code

```bash
claude mcp add --transport http orafabric https://orafabric.com/api/dev/mcp \
  --header "Authorization: Bearer $ORAFABRIC_API_KEY"
claude mcp list          # expect: orafabric  ✓ connected
```

### A3. Cursor / VS Code / Continue

Config snippets for each client are in [mcp-configuration.md](mcp-configuration.md).

### A4. Confirm the tools loaded

Ask your client, in plain language:

```
List the tools the orafabric server exposes, with the required parameters for each.
```

You should get six: `retrieve_evidence`, `check_relation`, `explore_concept`,
`get_paper`, `resolve_concept`, `get_coverage`.

If you get zero tools, the request reached the server but was not authorised — check the
`Authorization` header, not the URL.

### A5. First real query

```
Use orafabric. First call resolve_concept for "KRAS G12C" and tell me which node id is
an exact match. Then call retrieve_evidence with the query
"KRAS G12C inhibitor resistance mechanisms in non-small cell lung cancer".
For each finding, give me the claim, the source sentence in quotes, the study design,
the evidence strength, and the paper. Group them by whether they agree or disagree.
Finish with a list of what the evidence does not cover.
```

That prompt is deliberate. It forces the four things that separate this layer from a
search API: exact node resolution, source sentences, polarity, and an explicit statement
of what is missing.

---

## Path B — you are the client

### B1. Verify the connection

```bash
python examples/01-basic-mcp-connection/verify.py
```

This does a handshake, `tools/list`, and a free `get_coverage` call. It costs nothing.

Real output from a run of this repository:

```
endpoint         https://orafabric.com/api/dev/mcp
handshake        ok  protocol=2024-11-05  session=(none)
tools/list       ok  6 tools
                   retrieve_evidence  retrieve_evidence(query,max_evidence,include_hypotheses,filters)
                   check_relation     check_relation(subject,object,relation,both_directions,limit,filters)
                   explore_concept    explore_concept(concept,direction,relations,limit,filters)
                   get_paper          get_paper(id,include_findings)
                   resolve_concept    resolve_concept(name,type,limit)
                   get_coverage       get_coverage()
get_coverage     ok  datasets=25  concepts=23419720  relationships=39268665
                     updated_at=2026-11-06T14:44:11Z
```

### B2. Make one paid call

```bash
python examples/04-python-api-integration/main.py --query "EGFR resistance in lung cancer"
```

Costs $0.03. If it returns an empty pack, that is a coverage statement, not a bug — see
[Boundaries](../README.md#honest-boundaries--read-this-before-you-build).

### B3. Wire it into your app

`examples/04-python-api-integration/orafabric_mcp.py` is a single file, standard library
only, no dependencies. Copy it into your project. Details in
[api-integration.md](api-integration.md).

---

## What a call actually returns

`get_coverage` (free) — this is the shape, not a paraphrase:

```json
{
  "datasets": [
    { "id": 18, "name": "Antibody–Drug Conjugates & Targeted Payload Delivery" },
    { "id": 14, "name": "Biomarkers, Liquid Biopsy & Minimal Residual Disease" }
  ],
  "concepts": 23419720,
  "relationships": 39268665,
  "updated_at": "2026-11-06T14:44:11Z"
}
```

`resolve_concept` (free) — note the `id` format and the `match` field:

```json
{
  "candidates": [
    {
      "id": "25:kras g12c",
      "name": "KRAS G12C",
      "type": "Concept",
      "synonyms": ["KRAS G12C", "G12C"],
      "match": "exact",
      "score": 1
    },
    {
      "id": "21:kras",
      "name": "KRAS",
      "type": "Concept",
      "synonyms": ["K-ras", "KRASG12D", "KRAS Q61R"],
      "match": "fuzzy",
      "score": 0.5
    }
  ]
}
```

`retrieve_evidence` (paid) returns a pack with these top-level keys:

```
query        the query as received
datasets     which datasets the pack drew from
evidence     the findings — this is what you render
entities     the nodes involved
edges        typed relationships between them
paths        short chains through the graph
papers       paper metadata, when present
```

Every finding carries its own claim text, source sentence, study design / strength label
and a paper reference. Render **claim and source sentence together, always**. Shapes of
individual findings can vary slightly between dataset versions, so the examples read
them through a tolerant accessor and print raw JSON once on first use — copy that habit
into your own code rather than hard-coding field names.

---

## Cost and latency, before you build a UI

| Call | Cost | Observed latency |
|---|---|---|
| `get_coverage`, `resolve_concept` | free | ~0.2 s |
| `retrieve_evidence` | $0.03 | 11–50 s |
| `check_relation`, `explore_concept`, `get_paper` | $0.03 | ~2–26 s |

Two consequences for your product:

1. Set the HTTP timeout to **120–180 s**. A 30 s default will kill retrieval calls.
2. Never call `retrieve_evidence` inside a request handler without a cached or streamed
   response. Resolve names first with the free tool, then make one paid call.

Next: [tools-reference.md](tools-reference.md) for every parameter, or
[evidence-semantics.md](evidence-semantics.md) for how to present the results without
overstating them.
