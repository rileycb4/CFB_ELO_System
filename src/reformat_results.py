#!/usr/bin/env python3
"""Reformat a results CSV file in-place.

Rules:
- Keep only the first header row matching the expected columns.
- Remove numeric rankings in parentheses, e.g. "(22)".
- Remove any "@" characters.
- Drop the site column so the last four columns are team/score/team/score.
"""

from __future__ import annotations

import re
from pathlib import Path
import sys


HEADER = "Rk\tWk\tDate\tTime\tDay\tWinner\tPts\t\tLoser\tPts\tNotes"
OUTPUT_HEADER = "Rk, Wk, Date, Time, Day, Team Name, Score, Team Name, Score, Notes"


def reformat_text(text: str) -> str:
    lines = text.splitlines()
    out_lines: list[str] = []
    header_seen = False

    for line in lines:
        if not line.strip():
            continue
        if line.strip() == HEADER:
            if not header_seen:
                out_lines.append(OUTPUT_HEADER)
                header_seen = True
            continue

        cols = [c.strip() for c in line.split("\t")]
        cols = [re.sub(r"\(\d+\)\s*", "", c) for c in cols]
        cols = [c.replace("@", "").strip() for c in cols]

        # Drop the site column if present (blank/N between winner score and loser).
        if len(cols) >= 11:
            cols = cols[:7] + cols[8:]
        elif len(cols) == 10 and cols[7] in {"", "N"}:
            cols = cols[:7] + cols[8:]

        if len(cols) == 9:
            cols.append("")

        out_lines.append(", ".join(cols))

    return "\n".join(out_lines) + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: reformat_results.py <path-to-csv>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    original = path.read_text()
    path.write_text(reformat_text(original))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
