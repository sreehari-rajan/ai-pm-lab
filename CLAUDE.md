# Feedback Triage CLI

A Python command-line tool that classifies product feedback (theme, severity, one-line summary) with the Claude API, logs token usage, and lets me compute cost and compare results against my own hand labels. It is a learning project to build judgment about AI product behaviour, cost and failure modes. It is not a product.

Read `docs/PRD.md` before planning or writing code. It is the spec.

## How to work with me

- Before writing code for a new step, state your plan in under 15 lines and wait for my OK.
- Explain trade-offs briefly as you go. I want to understand the code, not just receive it.
- I write the cost calculation and the hand labels myself. Do not write cost logic or labels unless I ask.
- Keep functions small. Add a short README section for each step that works.

## Technical rules

- Language: Python, run inside the project's virtual environment (`.venv`).
- Models: `claude-haiku-5-5`, `claude-sonnet-5-5` and `claude-opus-5-5` (added 15 Nov for a comparison run). Set `max_tokens` to 600 (raised from 300 on 16 Nov after 5 of 40 Haiku calls were cut off at 300).
- Structured outputs: use `output_config.format` with type `json_schema` and `additionalProperties` false. Check the current docs (https://platform.claude.com/docs/en/build-with-claude/structured-outputs) instead of relying on memory. Do not use the older `output_format` beta-header form.
- Test runs: the CLI takes `--limit N` (default 5) and `--prompt baseline|rubric`, so test runs stay cheap and comparable.
- Files: input `data/feedback.jsonl` (`{id, text}` per line); output one file per model and prompt, `data/results_<model>_<prompt>.jsonl` (for example `data/results_claude-haiku-5-5_baseline.jsonl`), with the parsed fields plus `input_tokens` and `output_tokens` per call. Before a run, items already in that file with no error are skipped, so reruns don't duplicate rows or spend money; failed items are retried. A row that fails to parse also keeps the model's `raw_text`, so the cause can be read.
- Data: `make_sample.py` builds `data/feedback.jsonl` and `data/sample_meta.jsonl` from the raw CSV at `data/raw/dataset/dataset.csv`. Keep `data/` in `.gitignore`. Do not open `sample_meta.jsonl` while I am labelling.

## Safety rules

- The API key is `ANTHROPIC_API_KEY` in `.env`. Never read, print, stage or commit `.env`. Keep `.env` and `.venv` in `.gitignore`.
- Use public or synthetic data only. No employer data and no other confidential information.
- Never run loops or reruns without a `--limit`. The budget is a few dollars of API credit.
