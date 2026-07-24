#!/usr/bin/env python3
"""Fix YAML skills files so plain-scalar list items containing ': ' are quoted.

Unquoted colons make PyYAML parse the item as a mapping. We wrap those lines
in double quotes and escape internal double quotes.
"""
from __future__ import annotations

import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parent


def needs_quoting(content: str) -> bool:
    """Return True if a plain YAML scalar needs quoting."""
    stripped = content.strip()
    if not stripped:
        return False
    # Already quoted
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return False
    # Block scalar marker
    if stripped.startswith(">") or stripped.startswith("|"):
        return False
    # Contains colon-space or other YAML special characters at top level
    if re.search(r":\s", content):
        return True
    return False


def quote_content(content: str) -> str:
    # Wrap in double quotes; escape internal double quotes and backslashes.
    escaped = content.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def fix_line(line: str) -> str:
    m = re.match(r"^(\s+- )(.+)$", line)
    if not m:
        return line
    prefix = m.group(1)
    content = m.group(2)
    if needs_quoting(content):
        return f"{prefix}{quote_content(content)}\n"
    return line


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
