# ai-pm-lab

## Direct Anthropic API example

With your virtual environment active in PowerShell, install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Add your key to the `.env` file next to `hello_direct.py`:

```dotenv
ANTHROPIC_API_KEY=your-key-here
```

`PRICES` at the top of `hello_direct.py` includes these standard API rates in USD
per million tokens, checked against [Anthropic's official pricing](https://platform.claude.com/docs/en/about-claude/pricing)
on November 3, 2026:

| Model ID | Input | Output |
| --- | ---: | ---: |
| `claude-haiku-5-5` | $0.10 | $0.50 |
| `claude-sonnet-5-5` | $2.00 | $10.00 |
| `claude-opus-5-5` | $4.00 | $20.00 |
| `claude-fable-5-1` | $10.00 | $50.00 |

Haiku's listed rates apply to prompts up to 100,000 tokens, including this script's
short prompt. Estimates use standard global API pricing without prompt caching,
Batch discounts, or other surcharges. Update the dictionary if prices change.

Run with one of these model IDs:

```powershell
python .\hello_direct.py claude-haiku-5-5
```

The script sends one short prompt and prints the reply, input/output token counts,
request time in seconds (including any SDK retries), and estimated USD cost.
For unlisted model IDs, it explicitly reports that the cost is unavailable;
add the model's rates as an `(input_price, output_price)` tuple in `PRICES`.
The key can also come from an existing environment variable, which takes precedence
over `.env`. The `.env` file and virtual environments are ignored by Git.

## Feedback classifier (step 1: baseline, 5 items)

`cli.py` reads the first N items from `data/feedback.jsonl`, sends each one to the
model with a JSON schema (`output_config.format`, `json_schema`, `additionalProperties`
false), and appends one row per item to `data/results_<model>_<prompt>.jsonl`, for
example `data/results_claude-haiku-5-5_baseline.jsonl`. Items already in that file
with no error are skipped and counted, so a `--limit 2` run followed by `--limit 40`
only runs the remaining items. Failed items are retried, which adds a second row
for that id.

```powershell
python .\cli.py --model claude-haiku-5-5 --prompt baseline --limit 5
```

- `classify.py`: theme and severity enums, the schema, the baseline prompt, and the API call.
- `cli.py`: reads items, runs each one, and writes rows. A failed call or unparseable
  output is logged with `error` set, and the run continues.
- Each row holds `id`, `model`, `prompt`, the four result fields, `input_tokens`,
  `output_tokens` and `error`. Each model and prompt has its own file, so runs never mix.
  A row that fails to parse also holds `raw_text`, the model's raw output.
- The schema guarantees the shape of the output, not that the content is right, and it
  cannot enforce the 20-word summary limit. In the first 5-item run, 1 of 5 summaries (id 4) was 21 words.
- `max_tokens` is 600. At 300, 5 of 40 Haiku baseline calls were cut off before the JSON
  was finished, so the cap was raised for all models. A cut-off response is not valid JSON.
