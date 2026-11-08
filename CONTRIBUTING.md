# Contributing

The most useful contribution to this repository is **a bug report that reproduces**, and
the second most useful is **an example that runs on a clean machine**.

## Product bugs, coverage gaps, wrong findings

Open an issue with:

- output of `python examples/01-basic-mcp-connection/verify.py` (it redacts your key),
- the tool name and the exact arguments,
- the full error body or the finding you believe is wrong,
- if a finding looks misattributed: the claim, the source sentence, and the paper title
  (the title is usually enough to see that the sentence belongs to another topic).

Findings and coverage live in the service, not in this repository — but the repository is
where we track what developers hit.

## Adding an example

```
examples/NN-<slug>/
├── README.md        what it does, how to run it, what it costs
├── <script>.py      runnable, no secrets, no dataset dumps
└── prompts.md       optional, if the example involves a model
```

Rules for a PR:

1. **It runs.** `python <script>.py` on a clean machine with only `ORAFABRIC_API_KEY` set.
   Standard library preferred; if you add a dependency, pin it in `requirements.txt`.
2. **It states its cost.** "Three paid calls, $0.09" in the first paragraph.
3. **It states its limits.** Every example ends by saying what it does not do. That is
   not modesty, it is the product.
4. **No keys, no tokens, no real config files.** A PR containing a live key will be
   closed and the key revoked.
5. **No dataset dumps.** Do not commit large retrieval payloads. A trimmed 3-finding
   sample for a test fixture is fine.
6. **No invented tool names or parameters.** Copy them from `tools/list`.
7. **Honest output.** If your example produces a hypothesis, label it as one. Do not
   present an inference as a retrieved fact.

## Writing style for docs

- Say what happens, with the number, and where you saw it: "a retrieval pack took 23 s
  from this region", not "responses may be slow".
- Prefer a real error body over a description of an error.
- If a limitation is embarrassing, keep it. The repository's credibility rests on readers
  finding the caveats before they find the failure.

## Review

One maintainer review, focused on: does it run, does it state cost, does it overclaim. We
will usually suggest a wording change on the third point rather than reject the PR.

## Licence of contributions

By opening a PR you agree your contribution is licensed under the repository's MIT
licence, and that you have the right to submit it.
