# Tool calls behind this case study

The point of publishing the call log is that a reader can re-run it and see whether the
same findings come back. Without it, a case study is an anecdote.

The report records the log by **phase and focus** — twelve paid calls grouped five / four
/ two / one — plus three external searches and one full-text fetch. That grouping is
reproduced below exactly as the report states it. The literal strings were not published;
inventing them here would turn a documented method into a fabricated one, and a reader
re-running invented strings would get a different pack and blame the graph.

## The twelve calls

| Phase | # | Tool | Focus of the call | Why this call |
|---|---|---|---|---|
| Mapping | 1 | `retrieve_evidence` | pro-survival role | establish one half of the field's position |
| Mapping | 2 | `retrieve_evidence` | tumour-suppressive role | establish the other half |
| Mapping | 3 | `retrieve_evidence` | dual role / tumour stage | find the standard reconciliation *before* attacking it |
| Mapping | 4 | `retrieve_evidence` | KRAS dependence | a model-system axis, in case the sign tracks genotype |
| Mapping | 5 | `retrieve_evidence` | chloroquine / HCQ | the clinical-facing inhibitor, in case the sign tracks the drug |
| Tension | 6 | `retrieve_evidence` | autophagic cell death | the mechanism the field uses to explain cytotoxic outcomes |
| Tension | 7 | `retrieve_evidence` | flux completion vs accumulation | the discriminating variable — the hypothesis turns on this |
| Tension | 8 | `retrieve_evidence` | nutrient dependence | tests whether "cytotoxic" is really substrate exhaustion |
| Tension | 9 | `retrieve_evidence` | compartment | whether the sign tracks *where* autophagy happens |
| Refutation | 10 | `retrieve_evidence` | magnitude / threshold | try to kill the hypothesis with a dose effect |
| Refutation | 11 | `retrieve_evidence` | genetic ATG knockout, in vivo | try to kill it with an in-vivo arm |
| Boundary | 12 | `retrieve_evidence` | human tissue / prognosis | check whether any of it reaches patient data |

Two phases carry the method, and they are the ones worth copying:

- **The two refutation calls.** Eleven of the twelve look for what supports or characterises
  the claim. Two ask what would *destroy* it. A run with only the mapping phase produces a
  confident summary; a run with refutation calls produces the report on this page.
- **The boundary call.** One call is spent asking whether the phenomenon exists in human
  tissue at all. Its answer became the report's stated limit, not a footnote.

Free calls, which go first every time:

| Tool | Arguments | Why |
|---|---|---|
| `get_coverage` | — | record `updated_at`; a later reproduction is meaningless without it |
| `resolve_concept` | `{"name": "autophagy"}` | pin the anchor id before paying — a bare name can resolve to more than one node |
| `explore_concept` | `{"concept": "autophagy"}` | find the thin regions; this is where the gaps section comes from |

Cost: 12 × $0.03 = **$0.36**, plus `get_paper` at $0.03 for the papers carrying the load.

## What the report says about the run itself

- **One call timed out and was reissued with a simpler query.** Twelve is the number of
  calls that returned; the timeout stays in the log rather than being tidied away, because
  it is a real cost of a tool that runs 45–50 s.
- **Returns spanned 12 datasets**, principally Tumor Metabolism & Hypoxia, Cell
  Death/Senescence, Preclinical Models, NSCLC and Cell Therapy. If your reproduction lands
  on a different dataset mix, the graph moved underneath you — that is a coverage
  difference, not a contradiction.
- **The three external searches and the full-text fetch sit outside the twelve.** That is
  the step the graph cannot do for itself: the methodological case against the corpus rests
  on an externally retrieved article, and the pre-2020 foundational literature is outside
  the knowledge base entirely.

## Four claims that rest on a single paper

The report states these itself. A reproduction should check them first, because each is a
place where a thin base can look like a thick one:

1. each half of the central contradiction rests on **one paper** — neither is replicated
   inside this knowledge base;
2. the substrate-deficit sub-state rests entirely on **one glucose-rescue experiment**;
3. the arrest sub-state rests on **one paper plus a secondary interpretation** that is
   itself flagged for attribution;
4. the case against the whole corpus rests on **one externally retrieved article**.

## What "reproduced" means here

Re-running the phases above will not give byte-identical findings, and should not be asked
to. Compare these instead:

| Signal | Reproduced if |
|---|---|
| `get_coverage().updated_at` | same version → expect near-identical findings; newer → drift is legitimate |
| finding count and polarity split | the tension (`support` vs `contradict`) is still present |
| `source_section` on the A549 pair | still `results` / `discussion` — the contradiction is *inside* the papers, not across them |
| `evidence_strength_basis` | the two halves still disagree for a reason you can name |
| `paths` | empty before and empty now means the graph still offers no chain between the two anchors. Report that; do not fill it |

The comparison that matters is not "same 60 findings". It is: **did the disagreement
survive, and did the missing measurement still come back missing.** A run that returns
sixty concordant findings has reproduced nothing — it has found a different graph.

## An empty pack is usually phrasing

This is the behaviour that costs new users the most money. A query assembled from four
stacked technical terms returns nothing on a topic that is well covered; rewritten the way
the papers would write it, the same topic returns a full pack.

```
query A (0 findings):  "interferon signaling pathway defect IFNGR1 JAK1 JAK2 loss of function immune checkpoint resistance"
query B (60 findings): "JAK1 or JAK2 loss of function mutation causes resistance to immune checkpoint blockade"
```

That pair is from a real session. It is why the quickstart tells you to rewrite a query
before concluding "no evidence" — and why an empty result should be reported as a phrasing
result, not a coverage claim.

## Comparison discipline

Record, for any reproduction:

- `updated_at` from `get_coverage` at the start of the run;
- findings per call, and the polarity split within each pack;
- whether the specific load-bearing findings still come back, and whether their strength
  labels moved.

A finding that disappears entirely is something we want to know about — open an issue with
the query and the two `updated_at` values.

## Where to look next

The report's own verification priority ranks what breaks if a finding is mis-attributed.
Read that section before quoting a single finding from this pack: it is the difference
between citing a graph and citing a paper.
