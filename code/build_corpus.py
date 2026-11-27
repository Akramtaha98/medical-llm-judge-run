#!/usr/bin/env python3
"""Build the question/passage inventory and the frozen dev/test split from MedQuAD.

Usage:
  git clone https://github.com/abachaa/MedQuAD.git data/MedQuAD
  python code/build_corpus.py --medquad data/MedQuAD --out data/corpus --seed 2026

Outputs (in --out):
  inventory.csv : every candidate QA pair with source, ids, url, passage hash, status/exclusion reason
  reserve.csv   : remaining eligible items in a fixed order (for the minimum-yield rule only)
  selected.csv  : the chosen dev (12) and test (100) questions with frozen passages
  corpus_manifest.json : MedQuAD commit, parameters, counts, file hashes

Rules (protocol): Cancer.gov, NIDDK, NHLBI only; one question per source document; drop empty or
too short/long passages, duplicate questions and near-duplicate passages; stratified by source.
Selection uses a fixed seed and is reproducible. Review inventory.csv by eye before freezing.
"""
import argparse, csv, glob, hashlib, json, os, random, re, subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict

SOURCES = {"1_CancerGov_QA": "CancerGov", "5_NIDDK_QA": "NIDDK", "8_NHLBI_QA_XML": "NHLBI"}
MIN_W, MAX_W = 80, 300
N_DEV, N_TEST = 12, 100


def norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def shingles(t, n=5):
    w = re.findall(r"[a-z0-9]+", t.lower())
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def load(medquad):
    rows = []
    for folder, src in SOURCES.items():
        for path in sorted(glob.glob(os.path.join(medquad, folder, "*.xml"))):
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                rows.append({"source": src, "doc_id": os.path.basename(path), "status": "excluded:xml_parse_error"})
                continue
            doc_id, url, focus = root.get("id"), root.get("url", ""), norm(root.findtext("Focus"))
            for qa in root.iter("QAPair"):
                q = qa.find("Question"); a = qa.find("Answer")
                question = norm(q.text) if q is not None else ""
                passage = norm(a.text) if a is not None else ""
                rows.append({"source": src, "doc_id": doc_id, "question_id": q.get("qid") if q is not None else "",
                             "qtype": q.get("qtype") if q is not None else "", "focus": focus, "url": url,
                             "question": question, "passage": passage, "words": len(passage.split()),
                             "passage_sha256": sha(passage), "status": "candidate"})
    return rows


def screen(rows):
    seen_q = set()
    for r in rows:
        if r["status"] != "candidate":
            continue
        if not r["passage"] or not r["question"]:
            r["status"] = "excluded:missing_text"
        elif r["words"] < MIN_W:
            r["status"] = "excluded:passage_too_short"
        elif r["words"] > MAX_W:
            r["status"] = "excluded:passage_too_long"
        elif r["question"].lower() in seen_q:
            r["status"] = "excluded:duplicate_question"
        else:
            seen_q.add(r["question"].lower())


def one_per_document(rows, rng):
    by_doc = defaultdict(list)
    for r in rows:
        if r["status"] == "candidate":
            by_doc[(r["source"], r["doc_id"])].append(r)
    for _, grp in sorted(by_doc.items()):
        keep = rng.choice(grp)
        for r in grp:
            if r is not keep:
                r["status"] = "excluded:not_selected_for_document"


def drop_near_duplicates(rows, thr=0.8):
    kept = []
    for r in rows:
        if r["status"] != "candidate":
            continue
        s = shingles(r["passage"])
        if any(jaccard(s, k[1]) >= thr for k in kept):
            r["status"] = "excluded:near_duplicate_passage"
        else:
            kept.append((r, s))


def split(rows, rng):
    pool = defaultdict(list)
    for r in rows:
        if r["status"] == "candidate":
            pool[r["source"]].append(r)  # reserve items are marked after selection
    total = sum(len(v) for v in pool.values())
    need = N_DEV + N_TEST
    if total < need:
        raise SystemExit(f"Only {total} eligible items, need {need}. Relax MIN_W/MAX_W and document it.")
    quota, rem = {}, need
    srcs = sorted(pool)
    for s in srcs:
        quota[s] = min(len(pool[s]), round(need * len(pool[s]) / total))
    while sum(quota.values()) != need:  # fix rounding
        s = max(srcs, key=lambda x: len(pool[x]) - quota[x])
        quota[s] += 1 if sum(quota.values()) < need else -1
    chosen = []
    for s in srcs:
        pool[s].sort(key=lambda r: r["question_id"])
        rng.shuffle(pool[s])
        chosen += pool[s][:quota[s]]
    rng.shuffle(chosen)
    reserve = [r for s in srcs for r in pool[s][quota[s]:]]
    rng.shuffle(reserve)  # fixed order, used only if the minimum-yield rule needs more questions
    for i, r in enumerate(reserve):
        r["status"] = "reserve"; r["split"] = f"reserve_{i+1:03d}"
    for i, r in enumerate(chosen):
        r["split"] = "dev" if i < N_DEV else "test"
        r["status"] = "selected"
    return quota


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--medquad", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(a.seed)
    rows = load(a.medquad)
    screen(rows); one_per_document(rows, rng); drop_near_duplicates(rows)
    quota = split(rows, rng)
    cols = ["source", "doc_id", "question_id", "qtype", "focus", "url", "question", "words", "passage_sha256", "status", "split", "passage"]
    write_csv(os.path.join(a.out, "inventory.csv"), rows, cols)
    sel = sorted([r for r in rows if r["status"] == "selected"], key=lambda r: (r["split"], r["question_id"]))
    write_csv(os.path.join(a.out, "selected.csv"), sel, cols)
    res = sorted([r for r in rows if r["status"] == "reserve"], key=lambda r: r["split"])
    write_csv(os.path.join(a.out, "reserve.csv"), res, cols)
    counts = defaultdict(int)
    for r in rows:
        counts[r["status"]] += 1
    try:
        commit = subprocess.check_output(["git", "-C", a.medquad, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown (record manually)"
    man = {"medquad_commit": commit, "seed": a.seed, "word_range": [MIN_W, MAX_W], "n_dev": N_DEV, "n_test": N_TEST,
           "quota_by_source": quota, "status_counts": dict(counts),
           "selected_sha256": sha(open(os.path.join(a.out, "selected.csv"), encoding="utf-8").read())}
    json.dump(man, open(os.path.join(a.out, "corpus_manifest.json"), "w"), indent=2)
    print(json.dumps(man, indent=2))


if __name__ == "__main__":
    main()
