"""Classify one feedback item with the Claude API using a JSON schema."""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

THEMES = [
    "hardware_quality",
    "software_app",
    "connectivity",
    "price_value",
    "content_services",
    "ease_of_use",
    "general_praise",
    "other",
]
SEVERITIES = ["low", "medium", "high", "critical"]

SCHEMA = {
    "type": "object",
    "properties": {
        "theme": {"type": "string", "enum": THEMES},
        "severity": {"type": "string", "enum": SEVERITIES},
        "summary": {"type": "string"},
        "needs_human_review": {"type": "boolean"},
    },
    "required": ["theme", "severity", "summary", "needs_human_review"],
    "additionalProperties": False,
}

PROMPTS = {
    "baseline": (
        "Classify this product feedback. Give one theme, one severity, "
        "a one-line summary of at most 20 words, and whether a human should review it."
    ),
}

ROOT = Path(__file__).resolve().parent


def load_client() -> anthropic.Anthropic:
    """Build a client using ANTHROPIC_API_KEY from the project's .env file."""
    load_dotenv(ROOT / ".env")
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def parse_output(response) -> dict:
    """Return the parsed JSON from the response, or raise ValueError if it is unusable."""
    if response.stop_reason == "max_tokens":
        raise ValueError("output truncated at max_tokens")
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def classify(client: anthropic.Anthropic, model: str, prompt_name: str, text: str):
    """Send one feedback text to the model. Returns the raw response."""
    return client.messages.create(
        model=model,
        max_tokens=300,
        system=PROMPTS[prompt_name],
        messages=[{"role": "user", "content": text}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
