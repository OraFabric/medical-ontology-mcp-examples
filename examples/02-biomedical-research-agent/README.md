# Example 02 — Biomedical research agent

**Goal:** the orchestration a research Copilot needs, minus the model. The script does
retrieval, ranking and labelling deterministically; you attach an LLM only to write prose.

```bash
export ORAFABRIC_API_KEY=your_api_key_here

python agent.py "Explore the molecular mechanisms associated with KRAS G12C in lung cancer." \
               --anchors "KRAS G12C" "lung cancer"

python agent.py "Does current evidence support a direct causal relationship between lactate and CD8+ T-cell exhaustion?" \
               --anchors "lactate" "CD8+ T cell" --json > context.json
```

Cost: `$0.03` per retrieval attempt; a rewrite after an empty pack doubles it to `$0.06`.

---

## The four decisions in this script worth copying

### 1. Resolve before you retrieve

`resolve_concept` is free and returns node ids and a `match` field. Anchors that are
`fuzzy` are usually parent classes or cohort labels — passing them into a question quietly
changes what you asked about. The script prints what each name resolved to, so you can see
when a question has drifted.

### 2. Rewrite before you pay again

```
attempt 1: Does current evidence support a direct causal relationship between lactate and ...
           -> 0 findings. Rewriting before paying again.
attempt 2: lactate CD8+ T-cell exhaustion
           -> 41 findings
```

A pack that comes back empty is usually a phrasing problem, not a coverage hole. Rewriting
a query is free; re-running a paid call is not. Always alter the query between attempts
(see `docs/tools-reference.md`, "Phrase the query the way a paper would").

### 3. Rank with the free gate

```python
connects = mentions_both(claim + source_sentence, anchor_a, anchor_b)
```

Then by strength. That two-line sort is the difference between "here are 60 things near
your topic" and "here are the six findings that actually connect the two things you asked
about". Keep the filtered-out material below the fold if you like, but never at the top.

### 4. Label the claim type in the data, not in the prompt

`classify()` marks findings as `observed` or `interpretive` using a deliberately crude
regex on the claim text, and the label travels into the context block. Do not leave this
to the model: a model asked to "distinguish results from interpretations" will, sometimes,
fail silently. If the label is in the payload, the UI can enforce it.

The regex is a starting point, not an answer. The honest version of this step is a human-reviewed
labelling pass on the findings you actually display.

---

## Handing it to a model

`--json` emits:

```json
{
  "question": "...",
  "anchors": ["KRAS G12C", "lung cancer"],
  "coverage": { "datasets_in_pack": [...], "updated_at": null },
  "findings": [
    {
      "id": 1,
      "claim_type": "observed",
      "claim": "...",
      "source_sentence": "...",
      "strength": "moderate",
      "study_design": "...",
      "paper": { "id": "...", "title": "...", "journal": "...", "year": 2021 },
      "connects_both_anchors": true
    }
  ],
  "edges": [...],
  "paths": [...]
}
```

Send that as the user message, with [`prompts.md`](prompts.md) as the system prompt. The
finding `id` is what makes citation verifiable: the model cites `#3`, and `#3` is a specific
sentence in a specific paper.

---

## What this deliberately does not do

- **No hypothesis generation.** A model can propose one; this script will not, because
  proposing a mechanism from 20 extracted findings is exactly how you produce a
  confident-sounding fabrication.
- **No paper fetching.** Add `get_paper` for the papers you display: `$0.03` each, and
  the metadata makes a finding checkable by a reader.
- **No second-pass "deepening".** If you want a multi-turn traversal, the loop is
  `retrieve → find the empty region → ask a narrower question in that region`, and each
  narrowing costs `$0.03`. Budget it explicitly, because the interesting questions are
  where the graph is thin, and thin regions are where loops terminate.

---

## Files

| File | Role |
|---|---|
| `agent.py` | the orchestrator |
| `prompts.md` | the system prompt for the writing model |
