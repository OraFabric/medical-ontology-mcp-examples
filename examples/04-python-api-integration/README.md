# Example 04 — Python integration

**Goal:** put the retrieval layer inside your own application, with ranking, caching and
cost accounting that survive real users.

Two files:

| File | Role |
|---|---|
| `orafabric_mcp.py` | the client. Standard library only, ~130 lines. Copy it into your project. |
| `main.py` | a working single-question flow: coverage → resolve → retrieve → rank → report |

```bash
export ORAFABRIC_API_KEY=your_api_key_here

python main.py --query "EGFR resistance mechanisms in lung cancer"

python main.py --query "Does metformin improve response to immune checkpoint blockade?" \
               --anchor-a "metformin" --anchor-b "immune checkpoint inhibitor" \
               --papers 2
```

Cost: `$0.03` for the pack; `+$0.03` per paper requested. The script prints what it spent.

---

## Use it as a library

```python
from orafabric_mcp import OraFabricMCP, MCPError

client = OraFabricMCP()                                     # reads ORAFABRIC_API_KEY
pack = client.call("retrieve_evidence", {"query": "..."})    # $0.03, 11-50 s
for finding in pack["evidence"]:
    print(client.claim(finding), "|", client.strength(finding))
```

Three design points in the client worth copying into your own code:

1. **Business errors carry a code.** `ambiguous_concept`, `insufficient_balance`,
   `invalid_api_key`, `invalid_api_key`-family. Branch on `code`. Never parse the message.
2. **Retries only on transport failure.** Repeating a paid call whose business logic said
   no cannot succeed and does cost money.
3. **Tolerant field access.** `client.claim()`, `client.sentence()`, `client.strength()`
   read the first present key from a candidate list, because finding keys vary slightly
   between dataset versions. Hard-coding one key name is how examples rot.

---

## The flow, and why it is ordered that way

```
get_coverage        free    is the topic in scope at all?
resolve_concept     free    pin names to ids; catch ambiguity before paying
retrieve_evidence   $0.03   one call, phrased as a sentence
rank                free    both-endpoint filter, then strength
get_paper           $0.03   only for what you will display
```

**Ranking is the free part that decides quality.** `main.py` sorts findings by whether the
claim mentions both anchors, then by strength label. On real pairs this moves genuinely
on-topic evidence to the top and buries the incidental matches. Try it with and without
`--anchor-a/--anchor-b` and compare — the difference is the whole argument for using a
knowledge graph over a search box.

---

## What `main.py` deliberately does not do

- **It does not call an LLM.** The model is your layer, not the server's. Adding one is
  two lines: send the ranked findings plus the prompt in
  [`../02-biomedical-research-agent/prompts.md`](../02-biomedical-research-agent/prompts.md).
- **It does not cache.** For a single run that would be pointless. For a service, cache the
  pack by normalised query with a short TTL — see
  [`../../docs/api-integration.md`](../../docs/api-integration.md).
- **It does not prettify.** Output is plain text on purpose, so you can pipe it and see the
  raw sentences your users would be shown.

---

## Next

- [../../docs/evidence-semantics.md](../../docs/evidence-semantics.md) — before you render
  any of this to a clinician.
- [../../docs/api-integration.md](../../docs/api-integration.md) — caching, timeouts,
  multi-tenant keys, health-tech logging.
