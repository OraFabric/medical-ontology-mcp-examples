# Case study — autophagy block point

**Published report:** <https://doi.org/10.5281/zenodo.23904325>
**Zenodo record:** <https://zenodo.org/records/23904325> · Report v1.0 · CC BY 4.0

| | |
|---|---|
| Title | *Why does blocking autophagy sensitise cells to some drugs but rescue them from others?* |
| Subtitle | A hypothesis report on the boundary conditions separating cytoprotective from cytotoxic autophagy in therapy-treated cancer cells |
| Author | Wang Xiaofei (Ora Fabric (Singapore) Pte. Ltd.) |
| Issued | 2026-11-03 |
| Licence | CC BY 4.0 |
| Verdict, quoted from the report's abstract | "the sign is set by where the autophagic cycle is interrupted relative to where it was engaged — protective when autophagy follows damage and runs to completion, cytotoxic when completed flux consumes substrate the cell cannot replace or when flux arrests after initiation" |
| Retrieval behind it | 12 `retrieve_evidence` calls, plus 3 external searches and 1 full-text fetch |
| Status | Proposed. Untested. Never validated in a laboratory. |

---

## Why this is in a developer repository

Because a developer deciding whether to build on OraFabric needs one artefact that could
not have been produced by prompting a general model. This is it, and it is public and
citable.

The question is a real one that a research team would pay to answer: where is the actual
block point in autophagy, and which measurement has not been made? The output is not a
summary of the field. It is a hypothesis with a stated falsifier, a proposed experiment
with doses and controls, and an explicit list of what the graph could not see.

### What it found, in short

The field's usual reconciliation — autophagy is protective early, cytotoxic late, so the
sign depends on tumour stage — **fails on a single cell line.** In A549 lung
adenocarcinoma cells, knockdown of the *same* gene, ATG5, sensitises the cells to
gefitinib and rescues them from Cucurbitacin E. Stage, lineage and driver genotype are
constant across those two experiments, so the stage explanation cannot be what changes
the sign.

The report's replacement: the sign depends on **where the autophagic cycle is
interrupted relative to where it was engaged**. Protective when autophagy follows damage
and runs to completion; cytotoxic when completed flux consumes substrate the cell cannot
replace, or when flux arrests after initiation. The testable corollary is that upstream
and downstream blockade give *concordant* signs in the first two cases and *discordant*
signs in the third.

Three candidate explanations were tried and two were discarded. Tumour stage was
eliminated by an in-vivo finding that autophagy drives colorectal cancer initiation.

## Read it for four things in particular

1. **The tension it found.** Contradictions inside a single paper, and studies that
   point in opposite directions on the same relationship while differing in model system
   or dose. This is the layer a search box cannot produce, because a search box returns
   documents and this returns assertions with polarity.
2. **The gaps it declared.** Specific years, model systems and populations that returned
   nothing — stated as coverage statements rather than as facts about the world.
3. **The self-audit.** The report states what fraction of its evidence is incidental to
   the paper it came from, and flags findings for human attribution checks before
   publication. That habit is what makes the output usable by a researcher who will click
   through to the papers.
4. **What it did not claim.** No priority claim, no causal claim, no clinical
   recommendation — and it says so in the abstract, not in a footnote.

## What the report itself admits

Stated in the published abstract, not added here:

- it addresses **only therapy-treated cells** and says nothing about autophagy at tumour
  initiation;
- it **cannot be confirmed from this corpus**, because static LC3/p62 markers cannot
  distinguish high flux from stalled flux — the decisive measurement needs a flux assay;
- roughly **40 % of its cited evidence is incidental** to the source paper, and five
  findings carry an attribution flag for human checking;
- the **foundational pre-2020 literature falls outside the knowledge base**.

That last point is the one to internalise as a developer: absence inside this graph is
not absence of evidence.

## How it was produced

Multi-step traversal, not a single query — which is why a `retrieve_evidence` call alone
will not reproduce it:

```
resolve_concept          the anchor concepts                        free
retrieve_evidence        the map of what is known                  $0.03 per call
retrieve_evidence        queries aimed at disagreement
retrieve_evidence        queries aimed at killing each candidate
explore_concept          neighbourhood checks for thin regions     $0.03 per call
get_paper                metadata for the load-bearing papers      $0.03 per call
```

Twelve retrieval calls in total, four phases: mapping, tension, refutation, boundary.
The call log is in [`queries.md`](queries.md). Reproduction means re-running those phases
and comparing the findings you get back — the report logs the log by phase, not by literal
string, and this repository does not invent strings to look more reproducible than it is; the graph updates on a schedule, so a new dataset version can
legitimately return a different pack. Record the `updated_at` from `get_coverage` when you
reproduce a run, or the comparison means nothing.

## What a reader should take from it

Not "OraFabric found something". The claim in the report is narrower, and deliberately so:

> the graph made a contradiction legible, located a measurement that has not been
> reported, and then failed to settle the question — and the failure is written down.

A system that can only produce confident answers is not a research tool. A system that can
say "these two papers disagree, this variable differs between them, nobody has measured it
together, and here is the experiment" is one a researcher can use.

## Disclaimer

This report is a hypothesis generated by automated reasoning over a structured knowledge
graph. It has not been experimentally validated. The knowledge base covers open-access
publications in PubMed Central and oncology datasets only — absence inside it is not
absence of evidence. Extraction is automated and may misattribute a sentence to the wrong
paper; every finding should be checked against its source before being relied on.

Not medical advice.
