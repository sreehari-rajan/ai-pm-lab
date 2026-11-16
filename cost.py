"""Compute token cost per model and prompt from results files. Standard library only; makes no API calls."""

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

# USD per million tokens: (input, output). Same rates as PRICES in hello_direct.py.
RATES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

ROOT = Path(__file__).resolve().parent
DEFAULT_PATTERN = str(ROOT / "data" / "results_claude-*.jsonl")


def input_files(args: list[str]) -> list[str]:
    """Return the files to read: the default pattern if no args, else each arg expanded as a wildcard."""
    patterns = args or [DEFAULT_PATTERN]  # no args means the default pattern
    files = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if not matches:
            sys.exit(f"No files match: {pattern}")
        files.extend(matches)
    return files


def load_rows(paths: list[str]) -> list[dict]:
    """Read every non-blank JSON line from the given files."""
    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            rows.extend(json.loads(line) for line in f if line.strip())
    return rows


def row_cost(row: dict) -> float | None:
    """USD cost of one row, or None if the call had no tokens (an API error)."""
    if row["input_tokens"] is None:
        return None
    if row["model"] not in RATES:
        sys.exit(f"No rate for model: {row['model']}")
    in_rate, out_rate = RATES[row["model"]]
    return (row["input_tokens"] * in_rate + row["output_tokens"] * out_rate) / 1_000_000


def is_error(row: dict) -> bool:
    """True if the row has an api error, a parse error, or no tokens."""
    return row.get("error") is not None or row["input_tokens"] is None


def summarize(rows: list[dict]) -> dict:
    """Summary numbers for one (model, prompt) group."""
    priced = [r for r in rows if r["input_tokens"] is not None]  # rows that cost money
    total = sum(row_cost(r) for r in priced)
    count = len(priced)
    return {
        "rows": len(rows),
        "errors": sum(is_error(r) for r in rows),
        "avg_input": sum(r["input_tokens"] for r in priced) / count if count else 0,
        "avg_output": sum(r["output_tokens"] for r in priced) / count if count else 0,
        "cost_per_call": total / count if count else 0,
        "total": total,
    }


def group_rows(rows: list[dict]) -> dict:
    """Group rows by (model, prompt)."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["prompt"])].append(row)
    return groups


def print_group(key: tuple, s: dict) -> None:
    """Print one group's summary block."""
    model, prompt = key
    print(f"{model}  prompt={prompt}")
    print(f"  rows:              {s['rows']}")
    print(f"  errors:            {s['errors']}")
    print(f"  avg input tokens:  {s['avg_input']:.1f}")
    print(f"  avg output tokens: {s['avg_output']:.1f}")
    print(f"  cost per call:     ${s['cost_per_call']:.6f}")
    print(f"  cost per 1,000:    ${s['cost_per_call'] * 1000:.2f}")
    print(f"  total cost:        ${s['total']:.6f}")
    print()


def main() -> None:
    paths = input_files(sys.argv[1:])
    groups = group_rows(load_rows(paths))
    for key in sorted(groups):
        print_group(key, summarize(groups[key]))


if __name__ == "__main__":
    main()
