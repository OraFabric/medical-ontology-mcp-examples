# Prompt pack — evidence-based reasoning

Three prompts, in the order the dossier is built. Each one has a specific failure it
prevents; the failure is named so you can check whether it happened.

---

## Prompt 1 — classify the retrieved findings

```
You are given findings retrieved from a biomedical knowledge graph. For each finding,
assign exactly one label and do not merge categories:

OBSERVED      a result the authors measured
ASSOCIATION   a statistical relationship between two things
INTERPRETATION the authors' own reading of their data (look for: suggest, indicate,
              propose, may represent)
HYPOTHESIS    an explicitly untested proposal

For each finding also decide:
- does the claim connect BOTH entities in the question, or only one?
- is the claim central to the paper, or incidental (a side observation in a paper
  about something else)? Judge from the paper title versus the claim.

Output a table: id | label | connects | central/incidental | strength | paper.
Do not summarise the findings yet.
```

*Prevents:* a model quietly promoting an author's aside into a result.

## Prompt 2 — state the disagreement

```
Using only the table from step 1, write:

1. Where the findings agree, and how many independent papers that rests on.
2. Where they disagree. For each disagreement, name the study conditions that differ:
   population, model system, dose or concentration, timing, endpoint measured.
3. Which findings should be excluded from both sides, and why — one-endpoint findings,
   incidental findings, hypotheses.

Do not resolve the disagreement. Do not conclude. If the disagreement is an artefact of
different endpoints being measured, say that instead of picking a winner.
```

*Prevents:* the "averaging" failure, where two contradictory findings become "mixed
evidence, unclear" and the actual discriminating variable is lost.

## Prompt 3 — find the measurement nobody made

```
Given the findings above, identify measurements that have not been reported:

- markers that are studied separately but never measured together in one cohort
- populations mentioned in papers but never measured for this question
- model systems where the effect appears, and systems where nobody looked

For each candidate gap:
- state it as a runnable measurement: "in <population>, measure <A> and <B> together"
- cite the finding(s) that show each part has been studied alone
- state what a positive and a negative result would mean

If you cannot cite a finding for the claim that something has not been done, mark the
gap as UNVERIFIED and say which search would confirm it.
```

*Prevents:* the most damaging output this kind of system can produce — a confident
"nobody has studied this" that is really "my retrieval missed it".

That third prompt is the commercial one. A summary is a commodity; a specific, sourced,
runnable measurement gap is what a research team will pay attention to. Note the guard
rail: absence must itself be sourced, or it is a guess wearing a lab coat.

---

## Handing the model the data

Use the dossier JSON rather than the rendered markdown — the markdown has already made
editorial decisions, and asking a model to re-derive them invites drift:

```python
context = {
    "question": "Does lactate drive CD8+ T-cell exhaustion?",
    "findings": [...],          # with labels from prompt 1
    "coverage": {"datasets": [...], "updated_at": "..."},
}
```

Keep the finding `id` in the payload and require citations by id. Then check them:

```python
import re
cited = {int(n) for n in re.findall(r"\[#(\d+)\]", answer)}
assert cited <= {f["id"] for f in context["findings"]}
```

## Rendering rules for a clinician-facing UI

- Never collapse four label types into one confidence number.
- Show the source sentence, always, next to the claim.
- `moderate` = "one controlled study". Do not upgrade the wording.
- Keep the "not from the graph" boundary visible in the document, not in a tooltip.
- Print the coverage limits of that specific run, not a generic disclaimer.
