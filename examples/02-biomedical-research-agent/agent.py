#!/usr/bin/env python3
"""Example 02 — a biomedical research agent, without an LLM in the loop.

This is the orchestration skeleton you would hand to a model later:

    1. resolve the anchor concepts (free)
    2. retrieve one evidence pack for the question ($0.03)
    3. if the pack is empty, rewrite the query and try again (a rewrite is free,
       the call is not — so rewrite before paying, not after)
    4. rank findings: does the claim connect both anchors, then strength
    5. group them: observed / conflicting / interpretive
    6. emit a structured context block for your LLM, plus a human-readable digest

Run:

    export ORAFABRIC_API_KEY=your_api_key_here
    python agent.py "Explore the molecular mechanisms associated with KRAS G12C in lung cancer."
    python agent.py --json "..."        # machine-readable context block

Cost: $0.03 per retrieval attempt. A normal run is $0.03, a run that needed one rewrite
is $0.06.
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

# Phrases that mark an author's claim rather than an observed result. Crude, and
# deliberately visible: the point of this example is that you must label claim types,
# not that this regex is complete.
INTERPRETIVE = re.compile(
    r"(suggest|indicat|propose|hypothes|we believe|may represent|imply|could be)\w*", re.I
)


def rewrite_queries(question):
    """Cheap reformulations to try when a pack comes back empty.

    Four stacked technical terms often return nothing for a well-covered topic; a
    sentence phrased the way authors write it returns a full pack. Rewriting is free.
    """
    cleaned = re.sub(r"[?\"']", "", question).strip().rstrip(".")
    return [
        cleaned,
        re.sub(r"\b(direct|causal|relationship|mechanisms?)\b", "", cleaned, flags=re.I).strip(" ,"),
        " ".join(cleaned.split()[:9]),
    ]


def classify(finding, client):
    claim = client.claim(finding)
    if INTERPRETIVE.search(claim or ""):
        return "interpretive"
    return "observed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="the research question, in a sentence")
    parser.add_argument("--anchors", nargs="*", default=[], help="entities for the endpoint filter")
    parser.add_argument("--rewrites", type=int, default=1, help="extra attempts if the pack is empty")
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="print the context block only")
    args = parser.parse_args()

    spent, attempts, started = 0.0, 0, time.time()
    try:
        client = OraFabricMCP()
    except MCPError as exc:
        sys.exit("setup failed: %s" % exc)

    anchors = []
    for name in args.anchors:
        candidates = client.call("resolve_concept", {"name": name, "limit": 5}).get("candidates", [])
        exact = [c for c in candidates if c.get("match") == "exact"]
        best = (exact or candidates or [{}])[0]
        if best.get("name"):
            anchors.append(best["name"])
        print("resolved %-20s -> %s (%s)" % (name, best.get("id", "?"), best.get("type", "?")))

    pack = {}
    for query in rewrite_queries(args.question)[: 1 + max(0, args.rewrites)]:
        attempts += 1
        arguments = {"query": query}
        if args.max_evidence:
            arguments["max_evidence"] = args.max_evidence
        print("attempt %d: %s" % (attempts, textwrap.shorten(query, 110, placeholder=" ...")))
        pack = client.call("retrieve_evidence", arguments)
        spent += 0.03
        total = len(pack.get("evidence", []))
        print("           -> %d findings, %d entities, %d edges"
              % (total, len(pack.get("entities", [])), len(pack.get("edges", []))))
        if total:
            break
        print("           -> empty pack. Rewriting before paying again.")

    findings = pack.get("evidence", [])
    if not findings:
        print("\nNothing in coverage for this question. That is a coverage statement, not a bug.")
        print("Record it, check get_coverage, and tell the user the question is outside scope")
        print("instead of answering from general knowledge.")
        return

    def rank_key(finding):
        text = (client.claim(finding) or "") + " " + (client.sentence(finding) or "")
        connects = bool(len(anchors) >= 2) and client.mentions_both(text, anchors[0], anchors[1])
        return (0 if connects else 1, -STRENGTH_RANK.get(client.strength(finding) or "", -1))

    ranked = sorted(findings, key=rank_key)

    # ---- the structured block you hand to your LLM -------------------------------
    context = {
        "question": args.question,
        "anchors": anchors,
        "coverage": {
            "datasets_in_pack": pack.get("datasets"),
            "updated_at": None,
        },
        "findings": [
            {
                "id": index,
                "claim_type": classify(finding, client),
                "claim": client.claim(finding),
                "source_sentence": client.sentence(finding),
                "strength": client.strength(finding),
                "study_design": client.design(finding),
                "paper": client.paper_ref(finding),
                "connects_both_anchors": bool(len(anchors) >= 2) and client.mentions_both(
                    (client.claim(finding) or "") + " " + (client.sentence(finding) or ""),
                    anchors[0], anchors[1],
                ),
            }
            for index, finding in enumerate(ranked[:20], 1)
        ],
        "edges": pack.get("edges", [])[:40],
        "paths": pack.get("paths", []),
    }

    if args.json:
        print(json.dumps(context, ensure_ascii=False, indent=2))
        print("\n# spent $%.2f over %d retrieval attempts" % (spent, attempts), file=sys.stderr)
        return

    print("\n=== ranked findings " + "=" * 54)
    for finding in context["findings"][:8]:
        print("\n#%d [%s] [%s]%s" % (
            finding["id"], finding["strength"] or "?",
            "connects both" if finding["connects_both_anchors"] else "one endpoint only",
            " (author's interpretation)" if finding["claim_type"] == "interpretive" else "",
        ))
        print(textwrap.fill(finding["claim"] or "(no claim text)", 92,
                            initial_indent="  ", subsequent_indent="  "))
        if finding["source_sentence"]:
            print(textwrap.fill('"%s"' % finding["source_sentence"], 92,
                                initial_indent="  ", subsequent_indent="  "))
        paper = finding["paper"]
        if isinstance(paper, dict):
            print("  paper: %s (%s, %s)" % (paper.get("title", "?"),
                                            paper.get("journal", "?"), paper.get("year", "?")))
        elif paper:
            print("  paper: %s" % paper)

    interpretive = sum(1 for f in context["findings"] if f["claim_type"] == "interpretive")
    connected = sum(1 for f in context["findings"] if f["connects_both_anchors"])
    print("\n=== what this run can and cannot claim " + "=" * 39)
    print("  findings returned           %d" % len(findings))
    print("  of which author's view      %d  (must not be reported as results)" % interpretive)
    print("  connecting both anchors     %d  of the %d shown" % (connected, len(context["findings"])))
    print("  next: fill in the gaps section from the data — years, model systems, empty")
    print("        neighbours — and hand the context block to your model with the prompt")
    print("        in prompts.md. Keep observed / interpretation / hypothesis separate.")
    print("\nspent $%.2f in %.1fs" % (spent, time.time() - started))


if __name__ == "__main__":
    main()
