"""Command-line entry point: classify feedback items and append rows to data/results_<model>_<prompt>.jsonl."""

import argparse
import json
from pathlib import Path

import anthropic

from classify import PROMPTS, ROOT, classify, load_client, parse_output, response_text

FEEDBACK_PATH = ROOT / "data" / "feedback.jsonl"


def results_path(model: str, prompt_name: str) -> Path:
    """Results file for one model and prompt, e.g. data/results_claude-haiku-5-5_baseline.jsonl."""
    return ROOT / "data" / f"results_{model}_{prompt_name}.jsonl"


def load_done_ids(path: Path) -> set[int]:
    """Ids that already have a successful row in this results file (empty if no file)."""
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return {row["id"] for row in rows if row["error"] is None}


def read_items(limit: int) -> list[dict]:
    """Return the first `limit` items from data/feedback.jsonl."""
    with FEEDBACK_PATH.open(encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    return [json.loads(line) for line in lines[:limit]]


def build_row(item: dict, model: str, prompt_name: str, response=None,
              parsed=None, error=None, raw_text=None) -> dict:
    """Make one results row. Parsed fields are null when the call or parse failed."""
    row = {"id": item["id"], "model": model, "prompt": prompt_name}
    row["input_tokens"] = response.usage.input_tokens if response else None
    row["output_tokens"] = response.usage.output_tokens if response else None
    fields = ["theme", "severity", "summary", "needs_human_review"]
    row.update({key: (parsed or {}).get(key) for key in fields})
    row["error"] = error
    if raw_text is not None:
        row["raw_text"] = raw_text  # only on parse errors, so the cause can be read
    return row


def append_row(row: dict, path: Path) -> None:
    """Append one row as a JSON line to the given results file."""
    path.parent.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_item(client: anthropic.Anthropic, item: dict, model: str, prompt_name: str) -> dict:
    """Classify one item and return its results row, recording errors instead of stopping."""
    try:
        response = classify(client, model, prompt_name, item["text"])
    except anthropic.APIError as exc:
        return build_row(item, model, prompt_name, error=f"api: {exc}")
    try:
        parsed = parse_output(response)
    except (ValueError, KeyError, StopIteration) as exc:
        return build_row(item, model, prompt_name, response=response, error=f"parse: {exc}",
                         raw_text=response_text(response))
    return build_row(item, model, prompt_name, response=response, parsed=parsed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify feedback with Claude.")
    parser.add_argument("--model", required=True, choices=["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"])
    parser.add_argument("--prompt", default="baseline", choices=sorted(PROMPTS))
    parser.add_argument("--limit", type=int, default=5, help="number of items to run (default 5)")
    args = parser.parse_args()

    path = results_path(args.model, args.prompt)
    done = load_done_ids(path)
    items = read_items(args.limit)
    todo = [item for item in items if item["id"] not in done]
    print(f"Skipped {len(items) - len(todo)} items already in {path.name}")

    client = load_client()
    for item in todo:
        row = run_item(client, item, args.model, args.prompt)
        append_row(row, path)
        print(f"id {row['id']}: theme={row['theme']} severity={row['severity']} error={row['error']}")


if __name__ == "__main__":
    main()
