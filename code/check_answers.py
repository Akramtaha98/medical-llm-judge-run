#!/usr/bin/env python3
"""Quality-of-format check for Set A answers (does NOT judge medical correctness).
Usage: python code/check_answers.py data/setA/answers.jsonl
"""
import json, sys, statistics as st
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "data/setA/answers.jsonl"
rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
cut = [r for r in rows if r["answer"].rstrip()[-1:] not in ".!?"]
words = [len(r["answer"].split()) for r in rows]
print(f"{len(rows)} answers; {len(cut)} do not end in . ! or ? (possibly cut off; limit was {rows[0]["max_tokens"]} tokens)")
print(f"words: median {st.median(words)}, max {max(words)}, over 80 words: {sum(w > 80 for w in words)}")
print("cut-off by generator:", dict(Counter(r["generator"] for r in cut)))
for r in cut[:5]:
    print(" ", r["question_id"], r["generator"], "...", r["answer"][-70:].replace("\n", " "))
