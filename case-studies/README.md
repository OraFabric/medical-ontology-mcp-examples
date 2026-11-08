# Case studies

Published research produced with these tools, with enough detail to reproduce it.

A case study here is not marketing. It follows three rules:

1. **The report is public and separately citable** (DOI), not a screenshot.
2. **The tool calls are listed**, so a reader can re-run the same queries and see whether
   they get the same findings.
3. **The failures are in the text.** A case study that only shows a clean result is not
   evidence that the method works; it is evidence that someone edited.

| Case | Question | What it demonstrates |
|---|---|---|
| [`autophagy-block-point/`](autophagy-block-point/README.md) | Where is the real block point in autophagy, and what has not been measured? | multi-step traversal producing a falsifiable hypothesis, plus an honest account of what the graph could not see |
| *(add yours)* | | submit a PR — see [../CONTRIBUTING.md](../CONTRIBUTING.md) |

## Adding one

```
case-studies/<short-slug>/
├── README.md        what the question was, what was found, how to reproduce
├── queries.md       the call log: twelve calls, by phase, with what each was for
└── (optional) report.pdf, dossier.md, figures
```

Requirements for a PR:

- the DOI or public link to the report, if there is one;
- the tool call list, with arguments, in the order they were made;
- the number of paid calls, so readers can cost the run;
- the limitations section of the report quoted verbatim, not paraphrased.

We will not merge a case study that presents a hypothesis as a result. That is the one
rule we enforce without discussion.

## Why case studies belong in a developer repository

Because "what can it do" is not answered by a feature list. A developer who is deciding
whether to build on this wants to see one artefact that could not have been produced by
prompting a chat model. That is what these are.
