#!/usr/bin/env python3
"""Example 04 — calling OraFabric from your own application.

A single-question flow, with the ranking and the cost accounting you would actually
ship:

    coverage -> resolve -> retrieve -> rank (both-endpoint filter) -> optional get_paper

Run:

    export ORAFABRIC_API_KEY=your_api_key_here
    python main.py --query "EGFR resistance mechanisms in lung cancer" --papers 2

Cost: $0.03 for the retrieval pack, plus $0.03 for each paper you ask for.
"""

import argparse
import os
import sys as _sys


def _log(message):
    """Progress goes to stderr; stdout is reserved for payloads you may pipe."""
    print(message, file=_sys.stderr, flush=True)
import json
import sys
import textwrap
import time

from orafabric_mcp import OraFabricMCP, MCPError


def rank_findings(client, findings, anchors):
    """Order findings by whether they connect both anchors, then by strength.

    The endpoint test is the cheapest quality gate available: a knowledge graph matches
    sentences, so a relevant finding is not necessarily about the relationship asked
    about. See docs/evidence-semantics.md.
    """
    strength_rank = {"high": 3, "moderate": 2, "low": 1, "very_low": 0}

    def key(finding):
        text = client.claim(finding) + " " + client.sentence(finding)
        connects = bool(anchors) and client.mentions_both(text, anchors[0], anchors[1])
        return (0 if connects else 1, -strength_rank.get(client.strength(finding) or "", -1))

    return sorted(findings, key=key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="the research question")
    parser.add_argument("--anchor-a", default=None, help="first entity, for the endpoint filter")
    parser.add_argument("--anchor-b", default=None, help="second entity, for the endpoint filter")
    parser.add_argument("--papers", type=int, default=0, help="how many papers to fetch ($0.03 each)")
    parser.add_argument("--max-evidence", type=int, default=None, help="cap the pack size")
    parser.add_argument("--json", action="store_true", help="print the raw pack instead of a summary")
    args = parser.parse_args()

    spent = 0.0
    started = time.time()

    try:
        client = OraFabricMCP()
    except MCPError as exc:
        sys.exit("setup failed: %s" % exc)

    coverage = client.call("get_coverage")
    _log("coverage   datasets=%d  concepts=%s  relationships=%s  updated=%s"
          % (len(coverage.get("datasets", [])), coverage.get("concepts"),
             coverage.get("relationships"), coverage.get("updated_at")))

    anchors = []
    if args.anchor_a and args.anchor_b:
        for name in (args.anchor_a, args.anchor_b):
            candidates = client.call("resolve_concept", {"name": name, "limit": 3}).get("candidates", [])
            exact = [c for c in candidates if c.get("match") == "exact"]
            best = (exact or candidates or [{}])[0]
            _log("resolved   %-12s -> %s (%s)" % (name, best.get("id"), best.get("type")))
            if best.get("name"):
                anchors.append(best["name"])

    _log("retrieving ... (this takes 11-27 s)")
    arguments = {"query": args.query}
    if args.max_evidence:
        arguments["max_evidence"] = args.max_evidence

    pack = client.call("retrieve_evidence", arguments)
    spent += 0.03
    _log("retrieved  in %.1fs  findings=%d  entities=%d  edges=%d  paths=%d"
          % (time.time() - started, len(pack.get("evidence", [])), len(pack.get("entities", [])),
             len(pack.get("edges", [])), len(pack.get("paths", []))))

    if args.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
        _log("\nspent $%.2f" % spent)
        return

    findings = rank_findings(client, pack.get("evidence", []), anchors)
    if anchors:
        kept = sum(1 for f in findings
                   if client.mentions_both(client.claim(f) + client.sentence(f), anchors[0], anchors[1]))
        print("endpoint filter kept %d of %d findings mentioning both anchors" % (kept, len(findings)))

    print("\n--- top findings " + "-" * 60)
    for index, finding in enumerate(findings[:6], 1):
        claim = textwrap.shorten(client.claim(finding) or "(no claim text)", 220, placeholder=" ...")
        print("\n%d. [%s] %s" % (index, client.strength(finding) or "?", claim))
        design = client.design(finding)
        if design:
            print("   design: %s" % (design if isinstance(design, str) else json.dumps(design)[:120]))
        sentence = client.sentence(finding)
        if sentence:
            print("   source: \"%s\"" % textwrap.shorten(sentence, 260, placeholder=" ..."))
        paper = client.paper_ref(finding)
        if isinstance(paper, dict):
            print("   paper:  %s (%s, %s)  id=%s"
                  % (paper.get("title", "?"), paper.get("journal", "?"), paper.get("year", "?"),
                     paper.get("id", "?")))
        elif paper:
            print("   paper:  %s" % paper)

    if args.papers:
        seen = {}
        for finding in findings:
            paper = client.paper_ref(finding)
            paper_id = paper.get("id") if isinstance(paper, dict) else paper
            if paper_id and paper_id not in seen and len(seen) < args.papers:
                seen[paper_id] = True
        for paper_id in seen:
            detail = client.call("get_paper", {"id": paper_id, "include_findings": False})
            spent += 0.03
            print("\npaper %s: %s" % (paper_id, json.dumps(detail, ensure_ascii=False)[:400]))

    print("\n--- what the pack does not cover " + "-" * 40)
    print("Print this yourself, from the data: which years are thin, which model systems")
    print("are absent, which neighbouring concepts returned nothing. A specific gap is")
    print("worth more than a generic caveat. See docs/evidence-semantics.md.")
    print("\nspent $%.2f  elapsed %.1fs" % (spent, time.time() - started))


if __name__ == "__main__":
    main()
