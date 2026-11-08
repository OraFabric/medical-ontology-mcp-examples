#!/usr/bin/env python3
"""Capture the screenshots this repository needs, reproducibly.

Four shots, three of them automatable:

    1. demo-01-tools-loaded.png    terminal output of verify.py, rendered to a card
    2. demo-02-config-copy.png     console page with the copy button (needs your login)
    3. demo-03-evidence-panel.png  an evidence pack rendered as the product would show it
    (logo)                         orafabric-logo.png — export from the brand source, not here

Usage:

    # 1. terminal card — no login, no cost, honest output
    python capture.py terminal \
        --text tools-loaded.txt \
        --out ../demo-01-tools-loaded.png \
        --title "verify.py — six tools loaded, free coverage call"

    # 3. evidence panel — from a real retrieval pack you saved as JSON
    python capture.py evidence \
        --pack my-pack.json \
        --question "Does metformin improve response to immune checkpoint blockade?" \
        --anchors metformin "immune checkpoint inhibitor" \
        --out ../demo-03-evidence-panel.png

    # 2. console page — logs in once in a throwaway profile, then captures headless
    python capture.py console \
        --url "https://orafabric.com/dev/login?next=/dev" \
        --out ../demo-02-config-copy.png \
        --profile ./.profile

Requirements: Python 3.9+ and a Chromium/Chrome binary. No pip installs.
"""

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser

CHROMIUM_CANDIDATES = [
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/local/bin/chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

FONT_STACK = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', "
              "Arial, 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif")
MONO_STACK = "'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', 'Courier New', monospace"


def find_chromium(explicit=None):
    if explicit:
        return explicit
    for candidate in CHROMIUM_CANDIDATES:
        path = shutil.which(candidate)
        if path:
            return path
        if os.path.exists(candidate):
            return candidate
    sys.exit("no chromium/chrome found — pass --chromium /path/to/binary")


def trim_bottom(path, background, padding=36):
    """Crop the empty strip under the content. Optional: needs Pillow, skipped if absent."""
    try:
        from PIL import Image
    except ImportError:
        return
    hexcode = background.lstrip("#")
    target = tuple(int(hexcode[i:i + 2], 16) for i in (0, 2, 4))
    image = Image.open(path).convert("RGB")
    width, height = image.size
    limit = int(padding * image.size[1] / max(height, 1))
    last = height - 1
    while last > 0:
        row = [image.getpixel((x, last)) for x in range(0, width, 24)]
        if any(max(abs(a - b) for a, b in zip(pixel, target)) > 6 for pixel in row):
            break
        last -= 1
    keep = min(height, last + 1 + int(36 * (image.size[0] / 1180)))
    if keep < height - 8:
        image.crop((0, 0, width, keep)).save(path)


def render(binary, html_text, out_path, width, height, profile=None, background=None):
    """Write HTML to a temp file and let headless chromium screenshot it."""
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    handle, html_path = tempfile.mkstemp(suffix=".html")
    with os.fdopen(handle, "w", encoding="utf-8") as fh:
        fh.write(html_text)

    command = [
        binary, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",            # retina-quality output
        "--window-size=%d,%d" % (width, height),
        "--screenshot=%s" % out_path,
        "file://%s" % html_path,
    ]
    if profile:
        command.insert(1, "--user-data-dir=%s" % os.path.abspath(profile))
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=90)
    finally:
        os.unlink(html_path)

    if not os.path.exists(out_path):
        sys.exit("chromium did not produce %s" % out_path)
    if background:
        trim_bottom(out_path, background)
    size = os.path.getsize(out_path)
    print("wrote %s  (%d x %d @2x, %.0f KB)" % (out_path, width, height, size / 1024))


# --------------------------------------------------------------------------- shot 1

TERMINAL_PAGE = """<!doctype html>
<html><meta charset="utf-8"><body style="margin:0;background:#0d1117;padding:48px;">
<div style="font:600 15px/1.5 {font};color:#8b949e;margin:0 0 10px 4px;letter-spacing:.02em">
{title}</div>
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:26px 30px;
            box-shadow:0 12px 32px rgba(0,0,0,.35)">
<pre style="margin:0;font:400 14px/1.75 {mono};color:#c9d1d9;white-space:pre-wrap">{body}</pre>
</div>
<div style="font:400 12px/1.6 {font};color:#6e7681;margin:14px 0 0 4px">{foot}</div>
</body></html>"""


def shot_terminal(args):
    text = ""
    if args.text and args.text != "-":
        with open(args.text, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()
    text = text.rstrip("\n")
    body = html.escape(text)

    # Colour the success markers so the card reads at a glance.
    for token in (" ok ", "ok  ", "connected"):
        body = body.replace(html.escape(token), '<span style="color:#3fb950">%s</span>' % html.escape(token))

    page = TERMINAL_PAGE.format(
        font=FONT_STACK, mono=MONO_STACK, title=html.escape(args.title), body=body,
        foot=html.escape(args.foot),
    )
    height = args.height or _fit_height(text.count("\n") + 1, 26, 48 * 2 + 90)
    render(args.chromium_path, page, args.out, args.width, height, background="#0d1117")


def _fit_height(units, per_unit, chrome, minimum=320, maximum=3000):
    """Grow the canvas to the content instead of leaving a grey desert below it."""
    return max(minimum, min(maximum, chrome + int(units * per_unit)))


# --------------------------------------------------------------------------- shot 3

def pack_to_cards(pack, anchors, limit):
    """Turn a retrieval pack into finding cards, tolerantly.

    Field names vary slightly between dataset versions — read the first present key,
    exactly like the client does.
    """
    def field(item, *names, default=""):
        for name in names:
            value = item.get(name) if isinstance(item, dict) else None
            if value not in (None, "", [], {}):
                return value
        return default

    findings = pack.get("evidence") or pack.get("findings") or []
    if isinstance(findings, dict):
        findings = [findings]

    strength_rank = {"high": 3, "moderate": 2, "low": 1, "very_low": 0}
    cards = []
    for finding in findings:
        claim = field(finding, "claim", "statement", "finding", "text")
        sentence = field(finding, "evidence", "source_sentence", "sentence", "quote")
        strength = field(finding, "strength", "evidence_strength", "strongest_evidence_strength")
        basis = field(finding, "evidence_strength_basis", default={})
        design = field(basis, "study_design", "design") if isinstance(basis, dict) else basis
        design = design or field(finding, "study_type", "study_design", "design")
        paper = field(finding, "paper", "paper_ref", "paper_id", "source_paper", default={})
        text = (claim + " " + sentence).lower()
        connects = bool(len(anchors) >= 2 and all(a.lower() in text for a in anchors[:2]))
        cards.append({
            "claim": claim, "sentence": sentence, "strength": strength, "design": design,
            "paper": paper, "connects": connects,
        })

    cards.sort(key=lambda c: (0 if c["connects"] else 1,
                              -strength_rank.get(c["strength"] or "", -1)))
    return cards[:limit]


DANGLING = {"in", "of", "and", "for", "with", "on", "to", "the", "a", "by", "from", "at"}


def clean_title(title, limit=118):
    """Trim a title that ends on a preposition and long ones on a word boundary.

    Some records arrive with the headline cut mid-phrase. Printing that verbatim in a
    public screenshot looks like our error, so trim it cleanly and keep the paper id."""
    words = str(title or "").split()
    while words and words[-1].lower().strip(",.;:") in DANGLING:
        words.pop()
    text = " ".join(words)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def dataset_summary(names, limit=3):
    shown = names[:limit]
    rest = len(names) - len(shown)
    return ", ".join(shown) + (" — +%d more" % rest if rest > 0 else "")


def shot_evidence(args):
    with open(args.pack, encoding="utf-8") as fh:
        pack = json.load(fh)

    meta = {}
    if args.papers and os.path.exists(args.papers):
        with open(args.papers, encoding="utf-8") as fh:
            meta = json.load(fh)

    cards = pack_to_cards(pack, args.anchors, args.limit)
    if not cards:
        sys.exit("no findings in %s — is this a raw retrieve_evidence payload?" % args.pack)

    datasets = pack.get("datasets") or []
    names = []
    for dataset in datasets:
        names.append(dataset.get("name", str(dataset)) if isinstance(dataset, dict) else str(dataset))

    # Safety: a fixture must never end up looking like a real screenshot.
    banner = ""
    if pack.get("_fixture"):
        banner = ('<div style="background:#fee2e2;border:1px solid #fca5a5;color:#991b1b;'
                  'font:600 12px/1.5 %s;padding:9px 12px;border-radius:8px;margin-bottom:16px">'
                  'SAMPLE DATA — synthetic fixture, not a real retrieval. '
                  'Re-run this command with a real pack before publishing.</div>') % FONT_STACK

    rows = []
    for card in cards:
        paper = card["paper"]
        paper_id = ""
        if isinstance(paper, dict):
            paper_id = str(paper.get("id") or paper.get("paper_id") or "")
            paper_line = " · ".join(str(x) for x in (
                clean_title(paper.get("title")), paper.get("journal"), paper.get("year")) if x)
        else:
            paper_id = str(paper or "")
            record = meta.get(paper_id) if isinstance(meta.get(paper_id), dict) else {}
            paper_line = clean_title(record.get("title") or "")
            if record.get("pmid"):
                paper_line += " · PMID " + str(record["pmid"])
        strength = card["strength"] or "?"
        strength_colour = {"high": "#0f6f4a", "moderate": "#8a5a00",
                           "low": "#6b4a7a", "very_low": "#6b7280"}.get(strength, "#374151")
        pill_bg = {"high": "#e6f4ec", "moderate": "#fdf3df",
                   "low": "#f3eaf7", "very_low": "#f1f2f4"}.get(strength, "#f1f2f4")
        rows.append(f"""
        <div class="card">
          <div class="row">
            <span class="pill" style="color:{strength_colour};background:{pill_bg}">{html.escape(strength)}</span>
            <span class="meta">{html.escape(str(card['design']))[:70]}</span>
            {('<span class="tag">connects both anchors</span>' if card['connects'] else
             '<span class="tag muted">one endpoint only</span>')}
          </div>
          <div class="claim">{html.escape(str(card['claim']) or '(no claim text)')}</div>
          {('<div class="quote">“' + html.escape(str(card['sentence'])) + '”</div>'
            if card['sentence'] else '')}
          <div class="paper">{html.escape(paper_line) or 'paper'}
            {('<span class="pid">' + html.escape(str(paper_id)) + '</span>' if paper_id else '')}
          </div>
        </div>""")

    page = f"""<!doctype html><html><meta charset="utf-8"><body style="margin:0;background:#f6f7f8;
padding:44px 48px;font-family:{FONT_STACK};color:#111827;">
<div style="max-width:1080px;margin:0 auto">
  {banner}
  <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:6px">
    <div style="font:600 13px/1 {FONT_STACK};letter-spacing:.14em;color:#0f4c5c">ORAFABRIC · EVIDENCE PACK</div>
    <div style="font:400 12px/1 {FONT_STACK};color:#6b7280">{len(cards)} findings shown · $0.03</div>
  </div>
  <div style="font:600 22px/1.35 {FONT_STACK};margin:8px 0 4px">{html.escape(args.question)}</div>
  <div style="font:400 12px/1.6 {FONT_STACK};color:#6b7280;margin-bottom:22px">
    datasets: {html.escape(dataset_summary(names) or 'n/a')} · ranked by both-endpoint match, then strength
  </div>
  {''.join(rows)}
  <div style="font:400 11px/1.6 {FONT_STACK};color:#9ca3af;margin-top:18px">
    Every finding carries the sentence it came from. Strength is the study design, not a score.
  </div>
</div>
<style>
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;margin:10px 0;
  box-shadow:0 1px 2px rgba(16,24,40,.05)}}
.row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.pill{{font:600 11px/1 {FONT_STACK};padding:5px 9px;border-radius:999px;text-transform:lowercase}}
.meta{{font:400 11px/1.4 {FONT_STACK};color:#6b7280;flex:1}}
.tag{{font:500 10px/1 {FONT_STACK};color:#0f6f4a;background:#e6f4ec;padding:4px 7px;border-radius:5px}}
.tag.muted{{color:#6b7280;background:#f1f2f4}}
.claim{{font:500 15px/1.55 {FONT_STACK};color:#111827;margin-bottom:8px}}
.quote{{font:400 13px/1.65 {FONT_STACK};color:#4b5563;border-left:2px solid #d1d5db;padding-left:11px;
  margin-bottom:8px}}
.paper{{font:400 11px/1.5 {FONT_STACK};color:#9ca3af}}
.pid{{margin-left:6px;color:#c4c8ce}}
</style></body></html>"""

    units = sum(140 + (40 if card["sentence"] else 0) for card in cards)
    height = args.height or _fit_height(units, 1, 232 + (44 if banner else 0))
    render(args.chromium_path, page, args.out, args.width, height, background="#f6f7f8")


# --------------------------------------------------------------------------- shot 2

def shot_console(args):
    """Capture a logged-in console page.

    Consoles are behind auth, so this cannot be a pure one-liner: the script opens the
    page in a throwaway profile using your normal desktop browser session, waits for you
    to log in, and then screenshots headless with the same profile.
    """
    profile = os.path.abspath(args.profile)
    os.makedirs(profile, exist_ok=True)

    print("step 1: a browser window will open in a throwaway profile at")
    print("        %s" % args.url)
    print("        log in, navigate to %s, then come back here." % args.target)
    print("        the profile dir is %s — it is safe to delete afterwards." % profile)

    command = [
        args.chromium_path, "--user-data-dir=%s" % profile,
        "--no-first-run", "--no-default-browser-check",
        "%s#capture" % args.url,
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    input("\n        press Enter here once the page you want is on screen ... ")

    print("step 2: screenshot")
    render(args.chromium_path, "<html><body></body></html>", args.out, args.width, args.height,
           profile=profile)

    try:
        process.terminate()
    except Exception:
        pass

    render(args.chromium_path,
           "<!doctype html><html><body></body></html>",
           args.out, args.width, args.height, profile=profile)


# ------------------------------------------------------------------------ entry point

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chromium", dest="chromium_bin", default=None,
                        help="path to chromium/chrome if autodetection fails")
    subs = parser.add_subparsers(dest="command", required=True)

    term = subs.add_parser("terminal", help="render a text transcript as a card")
    term.add_argument("--text", default="-", help="file to render, or - for stdin")
    term.add_argument("--out", required=True)
    term.add_argument("--title", default="terminal")
    term.add_argument("--foot", default="no API key shown · runs in under a second · costs nothing")
    term.add_argument("--width", type=int, default=1080)
    term.add_argument("--height", type=int, default=0, help="0 = fit the content")

    ev = subs.add_parser("evidence", help="render a retrieval pack as an evidence panel")
    ev.add_argument("--pack", required=True, help="JSON payload from retrieve_evidence")
    ev.add_argument("--question", default="research question")
    ev.add_argument("--anchors", nargs="*", default=[], help="two entities for the endpoint tag")
    ev.add_argument("--limit", type=int, default=4)
    ev.add_argument("--papers", default=None,
                    help="JSON map of paper id to get_paper output, for titles")
    ev.add_argument("--out", required=True)
    ev.add_argument("--width", type=int, default=1180)
    ev.add_argument("--height", type=int, default=0, help="0 = fit the content")

    con = subs.add_parser("console", help="capture a logged-in console page")
    con.add_argument("--url", required=True, help="login url")
    con.add_argument("--target", default="/dev", help="path to reach after login")
    con.add_argument("--profile", default="./.profile", help="throwaway browser profile")
    con.add_argument("--out", required=True)
    con.add_argument("--width", type=int, default=1280)
    con.add_argument("--height", type=int, default=860)

    args = parser.parse_args()
    args.chromium_path = find_chromium(args.chromium_bin)

    if args.command == "terminal":
        shot_terminal(args)
    elif args.command == "evidence":
        shot_evidence(args)
    else:
        shot_console(args)


if __name__ == "__main__":
    main()
