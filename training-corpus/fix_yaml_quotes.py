#!/usr/bin/env python3
"""Fix YAML list items that start with a single-quoted substring but have
additional unquoted text on the same line. Wrap the whole item in double quotes.
"""
from __future__ import annotations

import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parent


def fix_line(line: str) -> str:
    # Match list item indentation and content.
    m = re.match(r"^(\s+- )'(.*)$", line)
    if not m:
        return line
    prefix = m.group(1)
    rest = m.group(2)
    # Find the closing single quote of the first quoted substring.
    close = rest.find("'", 0)
    if close == -1 or close == len(rest) - 1:
        # No closing quote or quote is at end -> already a valid single scalar.
        return line
    # There's text after the first quoted substring.
    # Wrap the entire content in double quotes, escaping internal double quotes.
    content = f"'{rest}"
    escaped = content.replace('"', '\\"')
    return f'{prefix}"{escaped}"\n'


def main() -> int:
    for path in sorted(CORPUS.glob("*/skills.yaml")):
        text = path.read_text(encoding="utf-8")
        new_lines = []
        changed = False
        for line in text.splitlines(keepends=True):
            fixed = fix_line(line)
            if fixed != line:
                changed = True
            new_lines.append(fixed)
        if changed:
            path.write_text("".join(new_lines), encoding="utf-8")
            print(f"fixed {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
