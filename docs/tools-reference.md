# Tools reference

Six tools. Two are free, four cost $0.03 per successful call. Parameter names below are
exactly as returned by `tools/list` — copy them.

```
retrieve_evidence(query, max_evidence, include_hypotheses, filters)
check_relation(subject, object, relation, both_directions, limit, filters)
explore_concept(concept, direction, relations, limit, filters)
get_paper(id, include_findings)
resolve_concept(name, type, limit)
get_coverage()
```

**Always call `resolve_concept` before a paid call.** It is free, it returns node ids, and
it is the difference between a full pack and an empty one.

---

## `get_coverage` — free

The graph's current self-description. Call it first in any session; it is also how you
decide whether to tell a user "we do not cover this" instead of guessing.

No parameters.

```json
{
  "datasets": [{ "id": 18, "name": "Antibody–Drug Conjugates & Targeted Payload Delivery" }],
  "concepts": 23419720,
  "relationships": 39268665,
  "updated_at": "2026-11-06T14:44:11Z"
}
```

`datasets` is the scoping mechanism: the graph is oncology-first, and the dataset list is
where you confirm that a topic is inside it. Do not hard-code the counts in your UI;
they change.

---

## `resolve_concept` — free

Matches a name, abbreviation or synonym to node ids.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | gene, drug, disease, or any label you saw in a paper |
| `type` | string | no | restrict to a node type |
| `limit` | integer | no | number of candidates to return |

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

Notes that will save you a bug:

- **`match` matters.** `exact` at score 1.0 is the node you named. `fuzzy` at 0.5 usually
  means a parent class or a cohort label — "Patients with KRAS G12C-mutant NSCLC" is a
  study population, not the mutation.
- **Node ids carry a prefix** (`25:`, `21:`, …) and are opaque. Use them as keys, never
  parse them into meaning.
- **Same display name can map to more than one node.** A bare drug name like `metformin`
  can return several candidates with the same `name`; the paid tools then reject it with
  `ambiguous_concept` (see `check_relation`). Disambiguate here, for free, and pass the
  fuller phrase — `Metformin (AMPK activator) treatment` — or the node id.
- **Type is not a guarantee.** The graph contains both biological entities and study
  entities; a concept that reads like a sentence is usually a cohort or a measurement
  definition, not a mechanism.

---

## `retrieve_evidence` — $0.03

The workhorse. Give it a research question in natural language; it returns an evidence
pack covering the whole knowledge base.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | a question or a statement of the topic, not keywords only |
| `max_evidence` | integer | no | cap the number of findings returned; default returns a full pack (~60 findings) |
| `include_hypotheses` | boolean | no | also return the hypothesis layer |
| `filters` | object | no | dataset / metadata narrowing |

Response — top-level keys:

| Key | Contents |
|---|---|
| `query` | the query as received |
| `datasets` | which datasets produced this pack |
| `evidence` | the findings. **This is what you render.** |
| `entities` | nodes involved, typically a few dozen |
| `edges` | typed relationships between those nodes |
| `paths` | short chains, as `"id|REL|id"` string arrays |
| `papers` | paper metadata, when present |

### What one question expands into

**One call is not one query.** The question is decomposed server-side into assertion-shaped
searches, and the pack is the union of what they return. For the question

> `Does metformin improve CD8 T cell function in hypoxic tumours?`

the call expanded into these ten searches (this is the expansion recorded for that
question — it is generated per question, so treat it as an example of the shape, not a
fixed template you can pattern-match on):

1. Metformin activates AMPK signaling in CD8 T cells and enhances their effector cytokine production under hypoxic conditions.
2. Hypoxia in the tumour microenvironment suppresses CD8 T cell proliferation and cytotoxic function through HIF-1alpha-dependent metabolic reprogramming.
3. Metformin reverses hypoxia-induced suppression of CD8 T cell mitochondrial respiration and interferon-gamma secretion in tumour infiltrating lymphocytes.
4. Metformin treatment increases intratumoural CD8 T cell infiltration and improves tumour control in hypoxic solid tumours.
5. Hypoxia reduces CD8 T cell cytotoxic granule release and metformin restores degranulation capacity in tumour-infiltrating lymphocytes.
6. Metformin improves CD8 T cell function in hypoxic tumours by inhibiting mitochondrial complex I and reducing reactive oxygen species in T cells.
7. Metformin fails to improve CD8 T cell effector function in hypoxic tumours when AMPK is genetically deleted in T cells.
8. Metformin combined with immune checkpoint blockade enhances CD8 T cell mediated tumour rejection in hypoxic tumour models.
9. Metformin at therapeutic concentrations increases CD8 T cell survival and effector memory differentiation in low oxygen tumour conditions.
10. Hypoxia-induced lactic acid accumulation impairs CD8 T cell function and metformin counteracts this metabolic suppression in the tumour microenvironment.

Three properties of this expansion matter more than the strings themselves:

- **They are claims, not keywords.** Each is a testable assertion with a subject, a
  relation and a polarity — that is why what comes back is a set of findings with
  `polarity`, not a set of documents.
- **At least one is a designed failure probe.** #7 asks where the effect *does not*
  appear (AMPK deleted), and #2 and #5 ask about the suppressive side rather than the
  rescue. A pack that only confirmed the question would be worthless: the disagreement is
  the product.
- **This is why the call is slow and why it costs what it costs.** Ten searches × graph
  traversal × 60 findings on the way out is ~45–50 s. Plan for it: do not hide this call
  behind a 30 s gateway timeout, and do not put it in a request handler that a user is
  staring at.

Read this list before you write your own `query`. A question that expands well is a
question with a direction, a condition and an outcome — "does X change Y under Z" — not
"X Y Z".

### The finding object, field by field

This is the exact shape returned on 2026-11-06 — copy the key names, they are not guesses:

```json
{
  "id": "21:combination metformin plus pembrolizumab in mice|INCREASES|21:cd8+ t cell infiltration",
  "claim": "Metformin plus pembrolizumab increases CD8+ T cell infiltration",
  "relation": "increases",
  "object": { "id": "21:cd8+ t cell infiltration", "name": "CD8+ T cell infiltration",
              "type": "Outcome", "synonyms": ["CD8+ T cell infiltration", "CD8+ T cells"] },
  "kind": "finding",
  "finding_type": "OBSERVED",
  "polarity": "positive",
  "certainty": "high",
  "scope": "study_specific",
  "evidence_strength": "moderate",
  "evidence_strength_basis": {
    "study_design": "animal_experiment", "outcome_directness": "direct",
    "precision": "not_reported", "risk_of_bias": "not_assessed",
    "consistency": "single_study"
  },
  "source_section": "results",
  "evidence": "the combination resulted in a remarkable CD8+ T cell infiltration",
  "paper_id": "112612"
}
```

| Key | What it is | How to use it |
|---|---|---|
| `claim` | one-sentence assertion | the line you render |
| `evidence` | **the source sentence, verbatim** | always show it — this is what makes a claim checkable. The key name reads like a flag; it is a string |
| `evidence_strength` | `high` / `moderate` / `low` / `very_low`, or `null` when uncomputable | bucket, don't score |
| `evidence_strength_basis.study_design` | `animal_experiment`, `cell_experiment`, `cohort`, … | the study design is **inside this dict**, not a flat key |
| `finding_type` | `OBSERVED`, and other kinds | never merge `OBSERVED` with hypothesis-layer items |
| `polarity` | `positive` / `negative` / `null` (direction of the effect) | this is where contradictions surface |
| `certainty` | pipeline confidence in the extraction | not the same as evidence strength |
| `scope` | `study_specific` and similar | tells you the claim does not generalise by default |
| `source_section` | `results`, `discussion`, … | a `discussion` claim is the authors' interpretation, not their result |
| `relation` + `object` | the predicate and the other endpoint | how the claim connects the two things you asked about |
| `paper_id` | opaque paper id | resolve it with `get_paper` |

Two consequences worth designing around:

- **`evidence_strength_basis` is a dict of five sub-ratings.** Show `study_design`; the rest
  is audit material for a human reviewer.
- **`source_section` is your cheapest guard against merging claim types.** Filter
  `discussion` out of a "results" panel and you have already avoided the most common error.

Measured behaviour you should design around:

- **Latency: 11–50 s for a full pack** (47.5 s observed on a 60-finding request). Set a
  120–180 s timeout; stream or cache in a UI. Do not put this behind a 30 s gateway limit.
- **A pack is broad, not precise.** It returns findings about the entities in your
  question, including some that are only incidentally related. Ranking is yours to do;
  `evidence-semantics.md` shows how.
- **The top-level `papers` array has been empty in every response observed.** Take the
  paper id from a finding and call `get_paper` when you need title/abstract metadata.
- **Phrase the query the way a paper would.** A query built from four stacked technical
  terms can return zero findings for a topic that is well covered; a sentence written as
  the authors would write it returns a full pack. Rewrite before you conclude "no
  evidence".
- **Zero findings is a coverage statement.** Cross-check with `get_coverage` and say
  "outside current coverage" rather than "no evidence exists".

---

## `check_relation` — $0.03

Evidence for, against and null on one named relationship between two named things.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `subject` | string | yes | a resolvable name; ambiguous names are rejected |
| `object` | string | yes | same |
| `relation` | string | no | constrain the relation type |
| `both_directions` | boolean | no | also look at `object -> subject` |
| `limit` | integer | no | per-bucket size (5 by default, 10 when set) |
| `filters` | object | no | dataset narrowing |

```json
{
  "subject": "...", "object": "...",
  "summary": { "by_relation": { "...": 3 } },
  "supporting": [ /* findings */ ],
  "contradicting": [ /* findings */ ],
  "no_effect": [ /* findings */ ],
  "hypotheses": [ /* findings */ ],
  "papers": []
}
```

**How to read it, and how not to.** The buckets are relevance-ranked evidence for the
subject and object, sized by the `limit` parameter. A non-empty `supporting` bucket means
"material relevant to the subject exists", not "the relationship is established".

Do not:

- publish "A causes B" because `supporting` is non-empty;
- infer absence of a relationship because `contradicting` is empty;
- compare bucket sizes between two questions as if they were a score.

Do:

- read each returned finding and check whether the claim actually connects **both**
  endpoints. Many findings mention only one. Filtering on that is the single biggest
  quality win available to you, and it costs nothing;
- keep `no_effect` and `hypotheses` separate in your UI, exactly as they arrive.

If one endpoint name matches several nodes, the call returns an
`ambiguous_concept` error and **is not billed**. Resolve the name, then retry once.

---

## `explore_concept` — $0.03

The neighbourhood of one node: upstream, downstream and associations.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `concept` | string | yes | resolvable name or node id |
| `direction` | string | no | `upstream` or `downstream` |
| `relations` | array of string | no | restrict relation types |
| `limit` | integer | no | neighbours per direction |
| `filters` | object | no | dataset narrowing |

```json
{
  "concept": { "id": "...", "name": "...", "type": "..." },
  "total_neighbors": 36,
  "neighbors": [
    {
      "concept": { "id": "...", "name": "...", "type": "...", "synonyms": [] },
      "direction": "downstream",
      "relation": "...",
      "findings": [ /* findings */ ],
      "papers": [ /* paper refs */ ],
      "strongest_evidence_strength": "moderate",
      "example": "..."
    }
  ]
}
```

Two parsing facts, both learned the hard way:

- **`strongest_evidence_strength` can be `null`.** Sort with a null-safe key or you will
  crash on real data.
- **Neighbours include study artefacts.** Cohorts, cohort sizes, cohort labels and
  measurement definitions sit in the graph alongside genes and drugs, and each may carry
  only one paper. Filter by `type` and by whether the neighbour looks like a biological
  entity before you draw a diagram.

Use it for navigation and for the "what surrounds this" panel in a UI. Do not present it
as a mechanism diagram — the edges are extracted associations, not a curated pathway.

---

## `get_paper` — $0.03

One paper and the findings extracted from it. **Does not return the article text.**

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | paper id as returned in a finding |
| `include_findings` | boolean | no | include the extracted findings |

Response (observed):

```json
{
  "paper_id": "112612",
  "title": "Metformin Combining PD-1 Inhibitor Enhanced Anti-Tumor Efficacy ...",
  "pmid": "35281267",
  "url": "https://pubmed.ncbi.nlm.nih.gov/35281267/",
  "findings_used": 0,
  "findings": []
}
```

`pmid` and a ready `url` come back, which is what makes a rendered finding checkable by a
human in one click. Titles occasionally arrive truncated mid-phrase — trim them for
display rather than printing a half sentence. One paid call per paper, so pick the
papers your answer actually depends on, not every paper in the pack.

---

## Cost control that actually works

1. `get_coverage` and `resolve_concept` on every session start — free.
2. One `retrieve_evidence` per question, with `max_evidence` set when you only need a
   handful.
3. `get_paper` only for the papers you will display.
4. Cache packs by normalised query. The graph updates on a schedule, not per second;
   a short TTL cache is almost always correct.
5. Never loop paid calls to "see if something shows up". If a query returns nothing,
   rewrite the query — that is free.
