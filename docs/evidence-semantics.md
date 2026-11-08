# Evidence semantics

This is the page to read before you put OraFabric output in front of a doctor, an
investor or a reviewer. It is about not overstating what a knowledge graph can tell you.

The short version: **a retrieval layer can tell you what the literature says and where it
disagrees. It cannot tell you what is true.** Your product's credibility depends on
keeping that line visible.

---

## 1. Four things that must never be merged

Extraction produces sentences. Sentences have four very different jobs, and they arrive
looking alike:

| Type | Example shape | What it licenses |
|---|---|---|
| **Observed result** | "TPS was ≥50% in 41 of 168 tumours." | the measurement, under those conditions |
| **Statistical association** | "High TPS was associated with improved PFS (HR 0.80)." | a correlation in that cohort |
| **Author interpretation** | "These data suggest TPS reflects pre-existing immunity." | the authors' view, not a finding |
| **Stated hypothesis** | "We hypothesise that IFN tone drives TPS." | nothing until tested |

If your prompt or your UI collapses these into one confidence score, you have built a
machine for manufacturing false certainty. Keep the label. When the source cannot be
classified with confidence, print the sentence and let the reader classify it.

Practical rules:

- A finding returned by a tool is **not** automatically an observed result.
- A high strength label on an author's interpretation is still an interpretation.
- Never restate `hypotheses` content as a finding. The tools return that bucket
  separately for exactly this reason — keep it separate.

---

## 2. The strength ladder

Strength is assigned by the system from the study design, not by a human reviewer, and it
describes the design behind the sentence:

| Label | Means |
|---|---|
| `high` | systematic review / randomised-trial level |
| `moderate` | a controlled single study — cohort, animal or cell |
| `low` | narrative review, case report or indirect inference |
| `very_low` | an author's assumption, no verification |

Two consequences:

- **`moderate` is the floor of this graph.** Most of what you get is single-study
  evidence. That is normal for mechanism questions, and it is fine — as long as your UI
  says "single study" rather than "evidence shows".
- **Strength is not relevance.** A `high` finding about a different population can be
  worthless for your question. Read the claim before you trust the label.

Always render strength next to the study design, not instead of it.

---

## 3. Polarity: what the buckets mean

`check_relation` returns `supporting`, `contradicting`, `no_effect` and `hypotheses` as
separate lists. Preserve that structure in your output.

- **Do not net them out.** "7 supporting, 2 contradicting" is not a score of +5. It is a
  description of the literature, and the two findings may be about different populations.
- **Do not treat an empty bucket as proof of absence.** It means the retrieval did not
  surface material, which is a statement about the graph and the query.
- **The presence of contradictions is the product, not a defect.** For most mechanism
  questions the honest answer is "the literature disagrees, and here is the variable that
  differs between the disagreeing studies". That answer is more valuable than a
  consensus summary, and almost no other tool can produce it.

---

## 4. The endpoint test — a free quality gate

A graph matches **sentences**, not subjects. A finding can be relevant to your question
and yet not be about the relationship you asked about.

Before you use any finding in a two-entity question, check whether the claim actually
mentions **both** endpoints. In our own testing this filter removed most of the returned
material for one pair and left clean, usable evidence for another — the difference between
a useful answer and a plausible-sounding one, at zero cost.

```python
def mentions_both(text, a, b):
    t = text.lower()
    return a.lower() in t and b.lower() in t
```

Apply it to claim plus source sentence. Keep the filtered-out material if you like, but
rank it below, or drop it. Never let it into the top of an answer.

---

## 5. Core versus incidental — the audit you must do yourself

Every finding should be tagged, because the strength label does not capture this:

- **`[core]`** — the claim is close to what the paper set out to study.
- **`[incidental]`** — the claim is a side observation in a paper about something else:
  a different molecule, a delivery system, a different disease, a cohort descriptor.

How to decide without reading every paper: look at the paper title next to the claim. If
the title gives no obvious reason for that claim to be in that paper, it is probably
incidental — and a specific number attributed to an unrelated paper is the most damaging
error you can ship. Flag it for human review rather than deleting it.

Report the ratio. "36% of the evidence used here is incidental" is a sentence that earns
trust. Hiding it does not.

Also state whether the field's **foundational papers are present at all**. A graph built
from open-access literature has structural blind spots: canonical work that is pre-2020
or paywalled simply is not there. When the classics are missing, your evidence base is
made of newer and more peripheral work than a specialist expects — say so in those words.

---

## 6. Rendering rules that keep you honest

Every displayed finding should carry, at minimum:

1. the claim,
2. the source sentence, quoted,
3. the paper (linked),
4. the study design,
5. the strength label,
6. the `[core]` / `[incidental]` tag once you have judged it.

For a whole answer:

- Separate **what the literature says** from **what the model concluded**. Different
  sections, different labels, no shared confidence score.
- State the limitations specifically. "Coverage may be incomplete" is useless. "No
  findings in human primary tissue after 2023 for this marker" is useful.
- If the evidence is too thin for the claim being asked, return that as the answer. A
  well-sourced "we cannot tell yet, and here is the measurement that would settle it" is
  a valid product output and, for research users, a more valuable one than a guess.

---

## 7. Things this layer cannot do — say so in your own docs too

- **It does not establish causality.** It reports what papers assert, with design and
  strength attached.
- **It does not rank papers for you.** Pooled meta-analytic numbers usually live in
  reviews that the graph may not contain; check before you claim an aggregate.
- **It cannot resolve a claim it cannot see.** Absence inside the graph is not absence of
  evidence in the world. Anything pre-2020 or paywalled may simply be missing — verify
  externally before making a novelty claim.
- **It will not replace a specialist's judgement.** It shortens the search; it does not
  end the argument.

A developer-facing integration that says all of this in its README is doing the brand a
favour. Users forgive limits that are declared; they do not forgive limits that are
discovered.
