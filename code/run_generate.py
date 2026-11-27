#!/usr/bin/env python3
"""Generate Set A answers (one per question) with Llama 3 or Qwen2.5, balanced within source.

Usage:
  python code/run_generate.py --selected data/corpus/selected.csv --out data/setA \
      --llama data/models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
      --qwen  data/models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf

Each question is answered once, in a fresh context, by exactly one generator (half and half within each
source, fixed seed). No answer is regenerated for quality reasons. Resumable. Models load one at a time.
Generation settings are the values to freeze in the protocol: temperature 0.3, top-p 0.9, seed 101, max 256 tokens (amendment #1).
"""
import argparse, csv, json, os, random, time
from collections import defaultdict

INSTRUCTION = ("Answer the reader's question in two or three short sentences for a general audience. "
               "Use only the supplied passage. If the passage does not answer the question, say so.")
TEMP, TOP_P, SEED, MAX_TOK = 0.3, 0.9, 101, 256


def assign(rows, seed=2026):
    """Equal halves within source x split; returns {question_id: generator}."""
    rng = random.Random(seed)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["source"], r["split"])].append(r["question_id"])
    out, flip = {}, 0
    for k in sorted(groups):
        ids = sorted(groups[k]); rng.shuffle(ids)
        first = ["llama3_8b", "qwen25_7b"][flip % 2]; flip += 1  # odd group sizes alternate the extra item
        second = "qwen25_7b" if first == "llama3_8b" else "llama3_8b"
        for i, q in enumerate(ids):
            out[(k[0], q)] = first if i % 2 == 0 else second  # keyed by (source, question_id): ids repeat across collections
    return out


def messages(passage, question):
    user = f"{INSTRUCTION}\n\n[PASSAGE]\n{passage}\n[/PASSAGE]\n\n[QUESTION]\n{question}\n[/QUESTION]"
    return [{"role": "user", "content": user}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--llama"); ap.add_argument("--qwen"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = list(csv.DictReader(open(a.selected, newline="", encoding="utf-8")))
    who = assign(rows)
    path = os.path.join(a.out, "answers.jsonl")
    done = set()
    if os.path.exists(path):
        done = {(d["source"], d["question_id"]) for d in map(json.loads, (l for l in open(path) if l.strip()))}
    paths = {"llama3_8b": a.llama, "qwen25_7b": a.qwen}
    with open(path, "a", encoding="utf-8") as out:
        for gen in ["llama3_8b", "qwen25_7b"]:
            todo = [r for r in rows if who[(r["source"], r["question_id"])] == gen and (r["source"], r["question_id"]) not in done]
            if not todo:
                continue
            llm = None
            if not a.dry_run:
                from llama_cpp import Llama
                llm = Llama(model_path=paths[gen], n_ctx=4096, n_gpu_layers=-1, verbose=False)
            for r in todo:
                t = time.time()
                if a.dry_run:
                    text = "Dry-run answer."
                else:
                    resp = llm.create_chat_completion(messages=messages(r["passage"], r["question"]),
                                                      temperature=TEMP, top_p=TOP_P, seed=SEED, max_tokens=MAX_TOK)
                    text = resp["choices"][0]["message"]["content"].strip()
                out.write(json.dumps({"question_id": r["question_id"], "source": r["source"], "split": r["split"],
                                      "generator": gen, "answer": text, "temperature": TEMP, "top_p": TOP_P,
                                      "seed": SEED, "max_tokens": MAX_TOK, "latency_s": round(time.time() - t, 2)},
                                     ensure_ascii=False) + "\n")
                out.flush(); os.fsync(out.fileno())
            del llm
    n = sum(1 for _ in open(path))
    print(f"answers written: {n} rows in {path}")


if __name__ == "__main__":
    main()
