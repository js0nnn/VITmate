"""Render the Mermaid diagrams embedded in docs/*.md to docs/pictures/.

The Markdown files are the single source of truth. Each diagram to export
starts with a Mermaid comment naming the output file:

    ```mermaid
    %% file: system-architecture
    flowchart TD
      ...
    ```

Requires mermaid-cli (https://github.com/mermaid-js/mermaid-cli) and a
Chrome/Chromium browser:

    npm install -g @mermaid-js/mermaid-cli     # or: set MMDC=/path/to/mmdc
    python scripts/render_diagrams.py

Set PUPPETEER_EXECUTABLE_PATH (e.g. /usr/bin/google-chrome) to use an
installed browser instead of the one Puppeteer downloads.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "pictures"
BLOCK = re.compile(r"```mermaid\n%% file: ([a-z0-9-]+)\n(.*?)```", re.DOTALL)


def find_diagrams() -> dict[str, tuple[str, str]]:
    diagrams: dict[str, tuple[str, str]] = {}
    for md in sorted(DOCS.glob("*.md")):
        for name, body in BLOCK.findall(md.read_text(encoding="utf-8")):
            if name in diagrams:
                sys.exit(f"Duplicate diagram name '{name}' in {md.name} and {diagrams[name][0]}")
            diagrams[name] = (md.name, body)
    return diagrams


def main() -> None:
    mmdc = os.environ.get("MMDC") or shutil.which("mmdc")
    if not mmdc:
        sys.exit("mermaid-cli (mmdc) not found. Install @mermaid-js/mermaid-cli or set MMDC.")
    diagrams = find_diagrams()
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        args: list[str] = []
        if os.environ.get("PUPPETEER_EXECUTABLE_PATH"):
            config = tmp_dir / "puppeteer.json"
            config.write_text(json.dumps({"executablePath": os.environ["PUPPETEER_EXECUTABLE_PATH"],
                                          "args": ["--no-sandbox"]}))
            args = ["-p", str(config)]
        for name, (source_file, body) in diagrams.items():
            src = tmp_dir / f"{name}.mmd"
            src.write_text(body, encoding="utf-8")
            for ext, extra in (("svg", []), ("png", ["-s", "2"])):
                subprocess.run([mmdc, *args, "-i", str(src), "-o", str(OUT / f"{name}.{ext}"),
                                "-b", "white", *extra], check=True, capture_output=True)
            print(f"rendered {name} (from {source_file})")


if __name__ == "__main__":
    main()
