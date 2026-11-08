# Assets

| File | What it shows | How it was made |
|---|---|---|
| `demo-01-tools-loaded.png` | `verify.py`: handshake ok, six tools listed, free coverage call | rendered from a real run; transcript in [`capture/tools-loaded.txt`](capture/tools-loaded.txt) |
| `demo-02-config-copy.png` | the developer console: create a key, and the **Copy** button that copies a complete MCP configuration | captured from the logged-in console; the key itself is masked, and the key list below the card is cropped out |
| `demo-03-evidence-panel.png` | an evidence pack: claim, source sentence, strength, paper, both-endpoint tag | rendered from a real `retrieve_evidence` pack, see [`capture/`](capture/README.md) |
| `orafabric-logo.png` | README header | brand mark, cropped to the artwork and resized to 512 px |
| `orafabric-social-preview.png` | GitHub → Settings → Social preview (1280×640) | composed from the mark on the brand green; regenerate only if the tagline changes |

The two rendered images come from real calls against the live endpoint. They are rendered
from the payload rather than pasted from a client window: that keeps them regenerable,
free of local paths and usernames, and honest — when the schema changes you re-run the
script instead of editing pixels.

Nothing here may contain a key, an email address, an avatar, or a file path.
[`capture/README.md`](capture/README.md) ends with the acceptance checklist to run before
committing a new image.

## Reproducing

```bash
cd assets/capture
export ORAFABRIC_API_KEY=...
python ../../examples/01-basic-mcp-connection/verify.py | tee tools-loaded.txt
python capture.py terminal --text tools-loaded.txt --out ../demo-01-tools-loaded.png \
  --title "verify.py — six tools loaded, free coverage call"
```

Commands for the evidence panel and the console shot, plus the auto-height and
sample-banner behaviour, are in [`capture/README.md`](capture/README.md).

Do not commit report PDFs here — they are citable artefacts and belong in
`case-studies/`, linked by DOI rather than copied.
