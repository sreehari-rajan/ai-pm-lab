"""Build feedback.jsonl: a de-duplicated, stratified sample of product reviews.

Usage:
    python make_sample.py data/raw/dataset/dataset.csv
    python make_sample.py data/raw/dataset/dataset.csv --seed 7 --out data/feedback.jsonl --meta data/sample_meta.jsonl

Outputs:
    data/feedback.jsonl     one {"id", "text"} per line. This is the ONLY file the classifier reads.
    data/sample_meta.jsonl  one {"id", "group", "rating", "product", "words"} per line.
                            Used later to report results per group. Do not open it until you have
                            finished labelling, so the star ratings do not bias your labels.

The same seed always produces the same sample, so the run is repeatable.
Standard library only.
"""
import argparse
import csv
import json
import random
import re
from collections import Counter

# (group name, min stars, max stars, how many items)
STRATA = [("negative", 1, 2, 15), ("mixed", 3, 3, 10), ("positive", 4, 5, 15)]

MIN_WORDS, MAX_WORDS = 15, 400  # drop one-liners and extreme outliers
LONG_WORDS, MAX_LONG = 250, 2   # allow at most 2 reviews over 250 words, to see their cost effect
MAX_PER_PRODUCT = 5             # keep one product from dominating the sample


def normalise(text):
    return re.sub(r"\s+", " ", text).strip()


def load_reviews(path):
    """Read the CSV; keep rated reviews of a usable length; drop exact duplicates."""
    csv.field_size_limit(10**9)
    seen, reviews = set(), []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            text = normalise(row.get("reviews.text") or "")
            try:
                rating = float(row.get("reviews.rating") or "")
            except ValueError:
                continue  # no star rating: skip, we need it to stratify
            words = len(text.split())
            if not (MIN_WORDS <= words <= MAX_WORDS):
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            reviews.append({
                "text": text,
                "rating": rating,
                "product": normalise(row.get("name") or "")[:60],
                "words": words,
            })
    return reviews


def pick(pool, n, rng, per_product, long_count):
    rng.shuffle(pool)
    chosen = []
    for review in pool:
        if len(chosen) == n:
            break
        if per_product[review["product"]] >= MAX_PER_PRODUCT:
            continue
        if review["words"] > LONG_WORDS:
            if long_count[0] >= MAX_LONG:
                continue
            long_count[0] += 1
        per_product[review["product"]] += 1
        chosen.append(review)
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path")
    parser.add_argument("--out", default="data/feedback.jsonl")
    parser.add_argument("--meta", default="data/sample_meta.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    reviews = load_reviews(args.csv_path)
    print(f"usable, de-duplicated reviews: {len(reviews)}")

    per_product, long_count, sample = Counter(), [0], []
    for group, low, high, n in STRATA:
        pool = [r for r in reviews if low <= r["rating"] <= high]
        chosen = pick(pool, n, rng, per_product, long_count)
        print(f"{group}: pool {len(pool)}, picked {len(chosen)} of {n}")
        for r in chosen:
            r["group"] = group
        sample.extend(chosen)

    rng.shuffle(sample)  # mix the groups so order gives no hints while labelling

    with open(args.out, "w", encoding="utf-8") as f_out, open(args.meta, "w", encoding="utf-8") as f_meta:
        for i, r in enumerate(sample, start=1):
            f_out.write(json.dumps({"id": i, "text": r["text"]}, ensure_ascii=False) + "\n")
            f_meta.write(json.dumps({"id": i, "group": r["group"], "rating": r["rating"],
                                     "product": r["product"], "words": r["words"]}, ensure_ascii=False) + "\n")

    words = sorted(r["words"] for r in sample)
    print(f"wrote {len(sample)} items to {args.out} and {args.meta}")
    print(f"words per item: min {words[0]}, median {words[len(words) // 2]}, max {words[-1]}")
    print("items per product:", dict(Counter(r["product"] for r in sample).most_common()))


if __name__ == "__main__":
    main()
