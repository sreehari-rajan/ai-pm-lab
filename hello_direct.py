import argparse
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
# USD/1M tokens (input, output); standard short-prompt rates, 2026-11-03.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0), "claude-fable-5-1": (10.0, 50.0),
}
parser = argparse.ArgumentParser(description="Send one short prompt to Claude.")
parser.add_argument("model", help="Anthropic model ID")
args = parser.parse_args()
load_dotenv(Path(__file__).with_name(".env"))
api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if not api_key:
    parser.exit(1, "Error: ANTHROPIC_API_KEY is missing from .env or environment.\n")
with anthropic.Anthropic(api_key=api_key) as client:
    start = time.perf_counter()
    try:
        response = client.messages.create(
            model=args.model, max_tokens=128,
            messages=[{"role": "user", "content": "Explain what an API is in one sentence."}],
        )
    except anthropic.APIError as exc:
        parser.exit(1, f"Anthropic API error: {exc}\n")
    elapsed = time.perf_counter() - start
print("Reply:", "".join(block.text for block in response.content if block.type == "text"))
usage = response.usage
print(f"Tokens: input={usage.input_tokens}, output={usage.output_tokens}")
print(f"Time: {elapsed:.3f} seconds")
rates = PRICES.get(args.model)
if rates is None:
    print("Estimated cost: unavailable; add this model's USD/1M token prices to PRICES.")
else:
    cost = (usage.input_tokens * rates[0] + usage.output_tokens * rates[1]) / 1_000_000
    print(f"Estimated cost: ${cost:.6f} USD")
