# PRD: Feedback Triage CLI (November build)

Nov 15, 2026 · Sreehari

## Intent

This build exists to give you first-hand judgment on how an AI feature behaves, costs money and fails. It is a learning vehicle, not a product.

You are building a small command-line tool that reads product feedback and returns a theme, a severity and a one-line summary as validated JSON. It is a base for later work on tool calling and evals.

After this build you should be able to:

- Explain tokens, input versus output pricing and cost per 1,000 calls, using numbers you measured on two model sizes.
- Explain why structured outputs make the format reliable but not the content correct.
- Judge when a cheaper model is good enough, using agreement with your own labels.
- Describe what happens when the output is wrong, and who pays for that error.

## Problem and user

Product teams receive more feedback than anyone can read, so someone has to sort it by theme and urgency before it can inform a roadmap decision.

- **Job to be done:** turn raw feedback text into consistent tags a PM can filter, count and escalate.
- **Primary user:** you, building and evaluating the tool to learn how AI features behave.
- **Imagined end user:** a PM triaging feedback. This persona is hypothetical; the build has no real users.
- **Manual alternative:** read and tag everything by hand, which is slow and varies between readers.

## Goals and non-goals

The build succeeds if you finish four things this week and can explain each one.

**Goals**

1. A command-line tool that classifies about 40 feedback items end to end.
2. Measured cost per call and per 1,000 runs for Haiku 5.5 and Sonnet 5.5, from logged tokens.
3. A hand-labelled set of 15–20 items, scored against both models and both prompt variants.
4. A README covering architecture, cost and what you learned.

**Non-goals**

- A web interface or deployment.
- Tool calling or agents (later).
- A full eval suite (later).
- Any confidential or proprietary data.
- Prompt tuning beyond the one second variant.

## Requirements

The tool reads feedback, classifies each item with a schema-constrained API call, logs tokens, and lets you compute cost and compare against your labels.

1. Read `data/feedback.jsonl`.
2. Send each item to the chosen model with the schema attached.
3. Write the parsed result and token counts to `data/results.jsonl`.
4. Compute cost and compare with `labels.jsonl`.

| Area | Requirement |
| --- | --- |
| Input | `data/feedback.jsonl`, one `{id, text}` per line; about 40 Amazon-device reviews from a Kaggle export, built by `make_sample.py` (seed 42): 15 rated 1–2 stars, 10 rated 3, 15 rated 4–5, shuffled. Stars and product go in `sample_meta.jsonl`, which stays closed until you finish labelling |
| Model | `--model` flag; run `claude-haiku-5-5` and `claude-sonnet-5-5`; `claude-opus-5-5` added 15 Nov for a comparison run |
| Test limit | `--limit N`, default 5, so you test cheaply before the full run |
| Output format | Structured outputs via `output_config.format`, type `json_schema`, `additionalProperties` false |
| Theme | One value per review from the theme list below: `hardware_quality`, `software_app`, `connectivity`, `price_value`, `content_services`, `ease_of_use`, `general_praise`, `other` |
| Severity | Enum: low, medium, high, critical. Praise-only reviews (`general_praise`) are `low` |
| Summary | String, at most 20 words |
| Human review flag | `needs_human_review`, boolean |
| Results file | `data/results.jsonl` with parsed fields plus `input_tokens` and `output_tokens` per call |
| Cost | You write it: a model-to-(input rate, output rate) dict, per million tokens; cost per call and per 1,000 runs |
| Call limits | `max_tokens` 300 |
| Secrets | `ANTHROPIC_API_KEY` in `.env`, which is gitignored and never committed |

**Prompt variants.** The `--prompt` flag selects `baseline` (a short instruction plus the schema) or `rubric` (adds a one-line definition and one example for each theme and severity level). Everything else stays fixed so the comparison is fair.

**Theme list.** Settled on 15 Nov 2026 after reading all 40 items. The classifier returns exactly one theme per review.

| Theme | Covers |
| --- | --- |
| `hardware_quality` | Build, durability, defects, fit, battery, sound or screen quality |
| `software_app` | Software, apps, updates, bugs, lag and slowness, voice assistant not understanding |
| `connectivity` | Bluetooth, Wi-Fi, pairing, connection drops |
| `price_value` | Cost, worth for the money |
| `content_services` | Movie, book and app catalogue, paywalls, store |
| `ease_of_use` | Setup, intuitiveness, instructions, accessibility |
| `general_praise` | Positive overall, no problem raised |
| `other` | Support, shipping, returns, nothing to classify |

Rules: a review that raises a problem gets the theme of its main problem, even if it also praises something. A review that only praises gets `general_praise` and severity `low`. Your labels use the same list and the same rules.

**Severity guide.** Severity is how much the problem affects the reviewer's use of the product, not the star rating or the tone. Your labels go in `data/labels.jsonl`: one theme and one severity per review, ids 1–20 plus id 26.

| Severity | Meaning | Made-up example |
| --- | --- | --- |
| `low` | No problem, or a minor annoyance or wish. No action needed. | "Works great, I just wish it came in blue." |
| `medium` | A real problem, but the product still works or has a workaround. | "Voice search misses my commands about half the time, but the buttons work fine." |
| `high` | The main function is broken or badly impaired. The reviewer returns it, regrets it or would not recommend it. | "Stopped working after two weeks and now won't turn on." |
| `critical` | Safety hazard, security or privacy exposure, or money lost with no remedy. Needs escalating. | "The charger overheated and smoked." |

Tie-breakers: for a mixed review, rate the main problem. Praise-only reviews are always `low`. Tone is not severity: all-caps anger about a small thing is still `low` or `medium`. When unsure between two levels, pick the lower one, unless safety or security is involved.

## Success metrics

The build is done when the tool runs cleanly on both models, you know what it costs, and you know how often it agrees with you. The agreement targets are proposed starting points; set them before you run, not after.

| Metric | Target (proposed) | Measured by |
| --- | --- | --- |
| Valid output | 40 of 40 items return schema-valid JSON on both models and both prompts | `results.jsonl` |
| Cost visibility | Cost per call and per 1,000 runs for both models and both prompts in the README | Logged tokens times rates |
| Theme agreement | At least 80% with your labels | `labels.jsonl` vs `results.jsonl` |
| Severity agreement | At least 70% with your labels | `labels.jsonl` vs `results.jsonl` |
| Spend | Under $1 of the $5 | Console usage page |
| Learning check | Explain tokens, input versus output pricing and what structured outputs guarantee, without notes | Self-test |

## Evaluation approach

Your own labels are the ground truth, so you label before you look at any model output.

1. Label 15–20 items for theme and severity in `labels.jsonl`. Pick one theme per review from the theme list.
2. Score agreement per field for each model and each prompt variant.
3. Read every disagreement and sort it: model wrong, label ambiguous, or theme list wrong.
4. Note which errors cost the most. A critical issue tagged "low" is far worse than the reverse.
5. Write down what you would change in the prompt, schema or model choice.

You label items 1–20 of the sample; it is already shuffled, so they mix all three groups. You also labelled item 26, chosen on purpose to include a critical case, so report it separately from the 20. Keep `sample_meta.jsonl` closed until you finish, so star ratings do not bias your labels. Then report agreement overall and per group (negative, mixed, positive). The pass marks apply to each model with its better prompt. Compare the two prompts on agreement, token cost and how often `needs_human_review` is true.

With 15–20 labels the scores are directional, not statistically solid. That is acceptable here: the set can seed a larger 50–100 case eval later and teaches you how to read disagreement.

## Constraints and guardrails

The budget is not the constraint; discipline about data, secrets and reruns is.

- **Budget:** $5 of Anthropic API credit (confirmed). One full run of 40 items on both models should cost about 8 cents. That is an estimate from roughly 500 input and 100 output tokens per call at the rates in `hello_direct.py`; your logs will give the real figure. With the longer rubric prompt added, one full set of runs should still stay well under $1.
- **Spend control:** test with `--limit 5` first, set `max_tokens`, and check the Console limits page for a spend cap.
- **Data:** a Kaggle export of Amazon-device reviews (licence: [CC0 1.0 Universal, public domain](https://creativecommons.org/publicdomain/zero/1.0/)); the raw CSV stays out of git. No confidential or proprietary data.
- **Secrets:** the API key lives in `.env`; check it is gitignored before the first commit.
- **Time:** a 2–3 hour weekend session today, then 1-hour weekday build slots.
- **Hardware:** everything runs on your laptop in VS Code, with a Python virtual environment and Claude Code in the integrated terminal; no cloud hosting is needed.

## Risks and decisions

The main risk is that AI writes the whole build and you learn little from it; the other risks are smaller and have simple fixes.

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Claude Code writes the older structured-output shape (`output_format` plus a beta header) | Code may not match the current API | Ask for `output_config.format` per the current docs; confirm with `--limit 5` |
| You learn little because AI writes everything | The point is judgment, not code | Write the cost calculation and the labels yourself; explain the results and cost figures unaided |
| Dataset licence is not visible in the file | Non-commercial terms would limit a public repo | Done: the Kaggle page lists CC0 1.0 (public domain). The raw CSV still stays out of git, and `feedback.jsonl` may be committed if you choose |
| Reviews are 2010–2017 Amazon-device reviews, not software feedback | Reviews cover hardware, accessories and streaming devices, so topics differ from software feedback (in your notes, 12 of 40 are hardware and 11 are software) | Theme list settled after reading the sample on 15 Nov; later add about 10 real public software reviews to see the gap |
| Only 66 distinct negative texts, and the source is mostly positive | A random sample would be mostly low severity, so agreement could look high by guessing | `make_sample.py` takes 15 negative, 10 mixed, 15 positive; report agreement overall and per group |
| Star ratings are not theme or severity labels | A 1-star review can be about shipping, not a defect | Use your own labels; keep `sample_meta.jsonl` closed until you finish |
| Theme list may not fit the feedback | About a third of the sample (14 of 40) is praise, which the starter list had no place for | Done: read all 40 items first and settled the list on 15 Nov; revisit it if labelling items 1–20 shows gaps |
| Only 15–20 labels | Agreement scores are noisy | Treat as directional; grow to 50–100 later |
| API key committed to GitHub | Key leaks and can be misused | Check `.gitignore` before the first commit |

**Decisions settled on 15 Nov 2026**

- The $5 is Anthropic API credit.
- Data: a Kaggle export of Amazon-device reviews, sampled by `make_sample.py` (seed 42) into 40 items: 15 negative, 10 mixed, 15 positive. The first, templated dataset is dropped.
- Pass marks stay at 80% for theme and 70% for severity.
- Theme list: eight values, one per review, settled after reading all 40 items. Added `connectivity`, `content_services` and `general_praise` (14 of 40 reviews are praise with no problem). Folded `battery` and `sound_display` into `hardware_quality`, and `support_returns` into `other`.
- Licence: the [Kaggle page](https://www.kaggle.com/datasets/yasserh/amazon-product-reviews-dataset) lists the dataset as [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) (public domain).
- Python, written and run in VS Code.
- A second prompt variant is in scope: `rubric` against `baseline`.

**Still open:** decide whether `feedback.jsonl` goes in the public repo (the licence allows it).

## Plan and deliverables

Today's 2–3 hour session gets a working classifier, a first cost figure and baseline runs; the Monday to Wednesday slots add labels, the second prompt and the README.

| Block | When and time | Output |
| --- | --- | --- |
| Setup check | Sun, 10 min | Key works, `.env` ignored |
| Dataset | Sun, 30 min | CSV at `data/raw/dataset/dataset.csv` (gitignored); `make_sample.py` builds `data/feedback.jsonl` with 40 reviews; you read all 40 and settle the theme list (done 15 Nov) |
| Classifier with Claude Code | Sun, 60 min | Working tool on 5 items, `baseline` prompt |
| Cost calculation, by hand | Sun, 15 min | Cost per call and per 1,000 runs |
| Full run, `baseline`, both models | Sun, 30 min if time allows, else Mon | `results.jsonl` for each model |
| Label items 1–20 and item 26, blind | Done 15 Nov | `labels.jsonl` |
| `rubric` prompt and scoring | Tue, 1 hr | Second set of results; agreement report for 2 models and 2 prompts |
| README and self-test | Wed, 1 hr | README with architecture, cost per 1,000 runs and lessons |

**Deliverable:** a GitHub repo with the tool, the data, the results and the README.

## Sources

- [Structured outputs, Claude Platform Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Amazon product reviews dataset, Kaggle (CC0 1.0)](https://www.kaggle.com/datasets/yasserh/amazon-product-reviews-dataset)
