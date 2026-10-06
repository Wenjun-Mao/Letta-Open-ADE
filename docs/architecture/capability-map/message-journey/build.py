"""Build the offline animated ADE diagram from its reviewed-source draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent
review = runpy.run_path(str(HERE / "review.py"))
OUTPUT = HERE / "ade-message-journey.html"
ASSETS = {
    "__STYLE__": "player.css",
    "__MODEL__": "flow-model.js",
    "__LAYOUT__": "flow-layout.js",
    "__VIEW__": "flow-view.js",
    "__PLAYER__": "player.js",
}


def fragment(figure: dict) -> str:
    source = (HERE / "player-template.html").read_text()
    encoded = json.dumps(figure, ensure_ascii=True, separators=(",", ":"))
    encoded = (
        encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )
    replacements = {
        "__FIGURE__": encoded,
        **{key: (HERE / name).read_text() for key, name in ASSETS.items()},
    }
    for marker, content in replacements.items():
        if source.count(marker) != 1:
            raise ValueError(f"Expected one template marker: {marker}")
        source = source.replace(marker, content)
    notice = (HERE / "THIRD_PARTY_NOTICES.md").read_text().replace("--", "- -")
    return f"<!--\n{notice}\n-->\n{source}"


def standalone(content: str) -> str:
    content = content.replace(
        '<section id="ade-moving-message"',
        '<section id="ade-moving-message" data-standalone',
        1,
    )
    return (
        """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADE - Journey of a message</title>
<style>
:root {
  color-scheme: light dark;
  --background: light-dark(#ffffff, #111418); --foreground: light-dark(#111418, #edf2f7);
  --card: light-dark(#ffffff, #1c232e); --muted: light-dark(#f5f7fa, #18212d);
  --muted-foreground: light-dark(#596575, #acb7c8); --border: light-dark(#ccd5e1, #3d4b60);
  --primary: light-dark(#111418, #edf2f7); --primary-foreground: light-dark(#ffffff, #111418);
  --viz-series-1: light-dark(#0074d9, #69b3ff); --ring: var(--viz-series-1);
  --journey-on-active: light-dark(#ffffff, #111418);
}
body { margin: 0; padding: 24px; background: var(--background); color: var(--foreground); font: 14px/1.5 "Avenir Next", sans-serif; }
main { max-width: 1920px; margin: auto; }
.text-small { font-size: 12px; }.text-muted { color: var(--muted-foreground); }
.tabular-nums { font-variant-numeric: tabular-nums; }
.btn, .form-select { font: inherit; padding: 8px 12px; color: var(--foreground); background: var(--card); border: 1px solid var(--border); border-radius: 8px; }
.btn-primary { background: var(--primary); color: var(--primary-foreground); }
button:disabled { opacity: .55; }button { cursor: pointer; }
button:focus-visible, select:focus-visible { outline: 2px solid var(--ring); outline-offset: 3px; }
@media(max-width:600px) { body { padding: 14px; } }
</style></head><body><main>"""
        + content
        + "</main></body></html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the tracked standalone presentation without writing",
    )
    parser.add_argument(
        "--inline-dir",
        type=Path,
        help="Also write a conversation fragment to this task-owned directory",
    )
    args = parser.parse_args()
    if args.check and args.inline_dir:
        parser.error("--check cannot write an inline fragment")
    figure, evidence, inventory = review["load"]()
    review["validate"](figure, evidence, inventory)
    content = fragment(figure)
    if len(content.encode()) >= 1_000_000:
        raise ValueError("Inline presentation exceeds 1 MB")
    output = standalone(content)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != output:
            raise SystemExit("Animated diagram is stale; run build.py")
        print(
            "Animated diagram matches the specification and editable presentation sources"
        )
        return
    OUTPUT.write_text(output)
    print(OUTPUT)
    if args.inline_dir:
        args.inline_dir.mkdir(parents=True, exist_ok=True)
        target = args.inline_dir / "ade-moving-message.html"
        target.write_text(content)
        print(target.resolve())


if __name__ == "__main__":
    main()
