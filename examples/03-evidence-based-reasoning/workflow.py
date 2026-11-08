#!/usr/bin/env python3
"""Example 03 — evidence-based reasoning over a question the literature disagrees on.

The scenario: does lactate drive CD8+ T-cell exhaustion, or does it also fuel them?
Both claims exist. This script builds a reasoning dossier from the graph:

    observed evidence      findings asserting an effect
    conflicting evidence   findings asserting the opposite or a null result
    mechanistic layer      transport / signalling findings that could mediate either
    what is missing        the specific measurement not made in one cohort

It does NOT produce the inference. It produces the structured base you would reason over,
and marks clearly where your own reasoning starts.

Run:

    export ORAFABRIC_API_KEY=your_api_key_here
    python workflow.py                      # writes lactate-cd8-dossier.md
    python workflow.py --out /tmp/d.md

Cost: three retrieval packs, $0.09.
"""

import argparse
import json
import os
import re
import sys
import textwrap
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "04-python-api-integration"))
from orafabric_mcp import MCPError, OraFabricMCP  # noqa: E402

STRENGTH_RANK = {"high": 3, "moderate": 2, "low": 1, "very_low": 0}

QUERIES = {
    "effect": "lactate suppresses CD8 T cell proliferation and effector function antitumor immunity",
    "counter": "lactate promotes CD8 T cell activation and antitumor immunity",
    "mechanism": "lactate transport MCT1 SLC16A1 signaling in CD8 T cell exhaustion",
}

NEGATIVE = re.compile(r"(no |not |fail|unaffected|did not|absence|null|contrary)", re.I)


def compact(client, finding):
    return {
        "claim": client.claim(finding),
        "sentence": client.sentence(finding),
        "strength": client.strength(finding),
        "design": client.design(finding),
        "paper": client.paper_ref(finding),
    }


def paper_line(paper):
    if isinstance(paper, dict):
        return "%s (%s, %s) — %s" % (
            paper.get("title", "?"), paper.get("journal", "?"),
            paper.get("year", "?"), paper.get("id", "?"),
        )
    return str(paper)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="lactate-cd8-dossier.md")
    parser.add_argument("--max-evidence", type=int, default=None)
    args = parser.parse_args()

    try:
        client = OraFabricMCP()
    except MCPError as exc:
        sys.exit("setup failed: %s" % exc)

    started, spent = time.time(), 0.0
    for anchor in ("lactate", "CD8+ T cell"):
        candidates = client.call("resolve_concept", {"name": anchor, "limit": 3}).get("candidates", [])
        best = ([c for c in candidates if c.get("match") == "exact"] or candidates or [{}])[0]
        print("resolved %-12s -> %s" % (anchor, best.get("id", "not found")))

    packs = {}
    for label, query in QUERIES.items():
        print("retrieving [%s] %s" % (label, textwrap.shorten(query, 70, placeholder=" ...")))
        arguments = {"query": query}
        if args.max_evidence:
            arguments["max_evidence"] = args.max_evidence
        packs[label] = client.call("retrieve_evidence", arguments)
        spent += 0.03
        print("            -> %d findings" % len(packs[label].get("evidence", [])))

    def sort(findings):
        return sorted(
            findings,
            key=lambda f: -STRENGTH_RANK.get(client.strength(f) or "", -1),
        )

    effect = sort(packs["effect"].get("evidence", []))
    counter = sort(packs["counter"].get("evidence", []))
    mechanism = sort(packs["mechanism"].get("evidence", []))

    # A crude split, and labelled as such in the output: a finding may belong to
    # "conflicting" only if its text asserts an opposite or null direction.
    counter_directional = [f for f in counter if NEGATIVE.search(client.claim(f) or "")]

    lines = []
    add = lines.append
    add("# Evidence dossier — lactate and CD8+ T-cell function\n")
    add("Generated %s · OraFabric knowledge graph · three retrieval packs · cost $%.2f\n"
        % (time.strftime("%Y-%m-%d"), spent))
    add("This dossier is a **retrieval product, not a conclusion**. Section 4 is clearly")
    add("marked as the author's own inference and does not come from the graph.\n")

    add("\n## 1. Observed evidence — effect asserted\n")
    for finding in effect[:8]:
        item = compact(client, finding)
        add("- **[%s]** %s" % (item["strength"] or "?", item["claim"] or "(no claim text)"))
        if item["sentence"]:
            add("  > \"%s\"" % item["sentence"])
        if item["design"]:
            design = item["design"] if isinstance(item["design"], str) else json.dumps(item["design"])
            add("  - design: %s" % design[:160])
        add("  - paper: %s" % paper_line(item["paper"]))

    add("\n## 2. Conflicting and null evidence\n")
    if counter_directional:
        for finding in counter_directional[:6]:
            item = compact(client, finding)
            add("- **[%s]** %s" % (item["strength"] or "?", item["claim"] or ""))
            if item["sentence"]:
                add("  > \"%s\"" % item["sentence"])
            add("  - paper: %s" % paper_line(item["paper"]))
    else:
        add("- No finding in the counter-query asserted an opposite direction. That is a")
        add("  statement about retrieval, not about the literature — check externally before")
        add("  claiming a consensus.")

    add("\n## 3. Mechanistic layer — transport and signalling\n")
    add("These findings do not settle direction; they are what a mechanism would run through.\n")
    for finding in mechanism[:6]:
        item = compact(client, finding)
        add("- **[%s]** %s" % (item["strength"] or "?", item["claim"] or ""))
        if item["sentence"]:
            add("  > \"%s\"" % item["sentence"])
        add("  - paper: %s" % paper_line(item["paper"]))

    add("\n## 4. Inference — NOT from the graph\n")
    add("> Everything below this line is the integrator's reasoning, not retrieved evidence.")
    add("> Keep this boundary visible in any UI that shows this dossier.\n")
    add("A defensible framing has to reconcile three facts at once:")
    add("the same metabolite suppresses effector function in some systems, appears to support")
    add("it in others, and acts through a transporter whose expression differs by cell state.")
    add("The variable that could reconcile them is not 'lactate yes/no' but **which arm of the")
    add("cell is measured and at which concentration**: a dose-and-time resolved readout in one")
    add("cohort, rather than more cross-study comparison.\n")
    add("What the graph does not contain: a single study measuring lactate exposure, transporter")
    add("expression and effector function together in the same cells. Until that exists, both")
    add("claims are supportable and neither is resolved.\n")

    add("## 5. How this would be falsified\n")
    add("A dose-response experiment in one model system, with transporter expression measured")
    add("per cell, showing that the suppressive effect persists when transport is saturated — that")
    add("would kill the reconciliation above. State the falsifier before running the experiment,")
    add("not after.\n")

    add("## 6. Coverage limits of this run\n")
    add("- %d findings from the effect query, %d from the counter query, %d mechanistic"
        % (len(effect), len(counter), len(mechanism)))
    add("- Coverage is oncology v1; immunometabolism work published outside oncology datasets")
    add("  will be missing.")
    add("- Findings are sentence-level extractions. Some are incidental to the paper they came")
    add("  from — check the title against the claim before relying on a number.")
    add("- No external verification was performed. Anything pre-2020 or paywalled is invisible")
    add("  to this graph, so 'nobody has measured this' is not a claim this run can make.\n")

    text = "\n".join(lines) + "\n"
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(text)

    print("\nwrote %s (%d lines)" % (args.out, len(lines)))
    print("spent $%.2f in %.1fs" % (spent, time.time() - started))
    print("\nRead section 4 with suspicion: it is marked as inference for a reason.")


if __name__ == "__main__":
    main()
