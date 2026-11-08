# Example 03 — Evidence-based reasoning

**Goal:** the thing this layer actually does that a search box does not — put the
disagreement on the table, with conditions attached, and mark exactly where your own
reasoning begins.

```bash
export ORAFABRIC_API_KEY=your_api_key_here
python workflow.py
```

Output: `lactate-cd8-dossier.md`. Cost: three retrieval packs, **$0.09**.

---

## Why this case

Lactate and CD8+ T cells is a live disagreement, not a settled fact:

- lactate is reported to suppress effector function and proliferation in several systems;
- the same metabolite is reported to support T-cell function in others;
- the transporter that gates the effect is expressed differently depending on cell state.

Any tool can return one side. The useful output is both sides plus **the variable that
differs between them**, because that variable is what a wet-lab researcher can go and
measure.

## The dossier structure

| Section | Source | What it is for |
|---|---|---|
| 1. Observed evidence | graph | findings that assert an effect |
| 2. Conflicting / null | graph | opposite or null directions, kept separate |
| 3. Mechanistic layer | graph | transport and signalling findings that could mediate either way |
| 4. Inference | **you** | explicitly marked as not from the graph |
| 5. Falsifier | **you** | the observation that would kill the framing |
| 6. Coverage limits | run metadata | what this run could not see |

Section 4 is the part reviewers will attack. It is fenced with a quote block and a warning
on purpose: if your UI renders a dossier like this, the boundary between "retrieved" and
"reasoned" has to be visible in the document, not in a footnote.

## The two habits this example teaches

**Keep the counter-query.** Querying only for the claim you expect produces a lopsided
dossier that reads like a conclusion. The second and third packs cost $0.06 and are the
reason the output is honest.

**Distinguish "no finding" from "no evidence in the world".** Section 2 prints a statement
about retrieval, not about the literature, when the counter-query returns nothing
directional. That sentence exists so that nobody mistakes the absence for a consensus.

## Files

| File | Role |
|---|---|
| `workflow.py` | builds the dossier |
| `prompts.md` | prompts for handing each section to a model, and for the inference step |

## Where to take it next

Take one section and deepen it: for a specific population, ask what has been measured
*together* in one cohort (`prompts.md`, prompt 3). That question is the one that produces
a research proposal rather than a summary.
