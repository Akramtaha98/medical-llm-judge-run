#!/usr/bin/env python3
"""Run one judge over the claim matrix (prompts x seeds) with llama.cpp. Resumable.

items.csv  : claim_id, passage, question, claim            (one row per claim, both sets)
runs.jsonl : appended; one line per (claim, judge, prompt, seed). Keys match analysis.py.

Sampled arm (primary): temperature 0.3, top_p 0.9, seeds 17/29/43.
Greedy arm (reference): temperature 0, seed 17; use --arm greedy and a separate --out file.
"""
import argparse, csv, json, os, sys, time, hashlib
from prompts import PROMPTS, build_messages, parse_label

SEEDS = [17, 29, 43]
MAX_TOKENS = 8  # the answer is one word; extra length is a format failure and parses as invalid
STOP = ["\n"]  # amendment #3: generation ends at the first newline; the strict whole-output parser is unchanged


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["claim_id"], r["judge_id"], r["prompt_id"], r["seed"]))
                except Exception:
                    pass  # a truncated last line is simply redone
    return done


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True, help="judge_id, e.g. llama3_8b or qwen25_7b")
    ap.add_argument("--model-path", help="path to the .gguf file")
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", choices=["sampled", "greedy"], default="sampled")
    ap.add_argument("--limit", type=int, default=0, help="first N claims only (timing pilot)")
    ap.add_argument("--n-ctx", type=int, default=4096)
    ap.add_argument("--dry-run", action="store_true", help="no model; fake labels to test resume and files")
    a = ap.parse_args()

    temp, top_p = (0.3, 0.9) if a.arm == "sampled" else (0.0, 1.0)
    seeds = SEEDS if a.arm == "sampled" else SEEDS[:1]

    with open(a.items, newline="", encoding="utf-8") as f:
        items = list(csv.DictReader(f))
    if a.limit:
        items = items[: a.limit]

    llm = None
    if not a.dry_run:
        from llama_cpp import Llama  # pip install llama-cpp-python (Metal build)
        llm = Llama(model_path=a.model_path, n_ctx=a.n_ctx, n_gpu_layers=-1, verbose=False)
        manifest = {"judge_id": a.judge, "model_path": os.path.basename(a.model_path), "sha256": sha256(a.model_path),
                    "arm": a.arm, "temperature": temp, "top_p": top_p, "max_tokens": MAX_TOKENS, "stop": STOP, "n_ctx": a.n_ctx,
                    "llama_cpp_python": __import__("llama_cpp").__version__, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(a.out + f".{a.judge}.manifest.json", "w") as m:
            json.dump(manifest, m, indent=2)

    done = load_done(a.out)
    total = len(items) * len(PROMPTS) * len(seeds)
    n, t0 = sum(1 for k in done if k[1] == a.judge), time.time()
    with open(a.out, "a", encoding="utf-8") as out:
        for it in items:
            for pid in PROMPTS:
                for seed in seeds:
                    key = (it["claim_id"], a.judge, pid, seed)
                    if key in done:
                        continue
                    t1 = time.time()
                    if a.dry_run:
                        raw = "UNSUPPORTED" if (hash((it["claim_id"], pid, seed)) % 3 == 0) else "SUPPORTED"
                    else:
                        r = llm.create_chat_completion(messages=build_messages(pid, it["passage"], it["question"], it["claim"]),
                                                       temperature=temp, top_p=top_p, seed=seed, max_tokens=MAX_TOKENS, stop=STOP)
                        raw = r["choices"][0]["message"]["content"]
                    lab = parse_label(raw)
                    rec = {"claim_id": it["claim_id"], "judge_id": a.judge, "prompt_id": pid, "seed": seed,
                           "parsed_label": lab, "status": "ok" if lab else "invalid", "raw": raw,
                           "arm": a.arm, "latency_s": round(time.time() - t1, 3)}
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush(); os.fsync(out.fileno())
                    n += 1
                    if n % 50 == 0:
                        el = time.time() - t0
                        print(f"{n}/{total} done, {el/60:.1f} min elapsed", file=sys.stderr, flush=True)
    print(f"finished {a.judge} ({a.arm}): {n}/{total} rows in {a.out}")


if __name__ == "__main__":
    main()
