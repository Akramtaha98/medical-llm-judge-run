#!/usr/bin/env python3
"""Uniqueness and key-consistency tests. Run from the repo root:  python code/test_keys.py
Data-dependent checks are skipped if the file is absent. Exit code 1 if any check fails."""
import csv, hashlib, json, os, subprocess, sys, tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from qkeys import qkey

SELECTED_SHA256 = "c75d52a934b332c178bd775431e1440765bef54f2216bee4bee0e86c61b61a49"  # frozen (build_corpus.py, seed 2026)
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        fails.append(name)


def rd(p):
    return list(csv.DictReader(open(p, newline="", encoding="utf-8")))


def exists(p):
    ok = os.path.exists(p)
    if not ok:
        print("SKIP " + p + " (not found)")
    return ok


sel_p = "data/corpus/selected.csv"
if exists(sel_p):
    # same convention as build_corpus.py: hash of the text read in text mode (newlines normalised), re-encoded as UTF-8
    sha = hashlib.sha256(open(sel_p, encoding="utf-8").read().encode("utf-8")).hexdigest()
    check("selected.csv hash unchanged", sha == SELECTED_SHA256, sha)
    sel = rd(sel_p)
    keys = [qkey(r["source"], r["question_id"]) for r in sel]
    check("selected.csv: (source, question_id) unique", len(keys) == len(set(keys)))
    raw = Counter(r["question_id"] for r in sel)
    print("INFO raw question_id repeated across sources:", [k for k, v in raw.items() if v > 1])
    selmap = {qkey(r["source"], r["question_id"]): r for r in sel}

    import run_generate
    who = run_generate.assign(sel)
    check("assign: every (source, question_id) gets a generator", set(who) == {(r["source"], r["question_id"]) for r in sel})
    grp = Counter((r["source"], r["split"], who[(r["source"], r["question_id"])]) for r in sel)
    halves_ok = all(abs(grp[(s, sp, "llama3_8b")] - grp[(s, sp, "qwen25_7b")]) <= 1 for s, sp in {(r["source"], r["split"]) for r in sel})
    check("assign: halves within source x split differ by at most 1", halves_ok)
    ans_p = "data/setA/answers.jsonl"
    if exists(ans_p):
        ans = [json.loads(l) for l in open(ans_p) if l.strip()]
        check("answers: one per (source, question_id)", len({(a["source"], a["question_id"]) for a in ans}) == len(ans) == len(sel))
        mism = [(a["source"], a["question_id"], a["generator"], who[(a["source"], a["question_id"])]) for a in ans
                if who[(a["source"], a["question_id"])] != a["generator"]]
        print("INFO answers whose recorded generator differs from the corrected assignment:", mism)

    for name, p in (("segmentation_review.csv", "data/claims/segmentation_review.csv"), ("claims_A.csv", "data/claims/claims_A.csv"),
                    ("claims_B.csv", "data/claims/claims_B.csv")):
        if exists(p):
            rows = rd(p)
            check(f"{name}: claim_id unique", len({r["claim_id"] for r in rows}) == len(rows))
            check(f"{name}: every question_id is a known composite key", all(r["question_id"] in selmap for r in rows))
            check(f"{name}: source matches selected.csv", all(selmap[r["question_id"]]["source"] == r["source"] for r in rows if r["question_id"] in selmap))
            if name.startswith("segmentation"):
                check("segmentation_review.csv: covers all 112 questions", len({r["question_id"] for r in rows}) == len(sel))
    p = "data/claims/setB_worksheet.csv"
    if exists(p):
        rows = rd(p)
        check("setB_worksheet.csv: 112 unique question keys equal to selected.csv", {r["question_id"] for r in rows} == set(selmap) and len(rows) == len(selmap))
        c = Counter((r["source"], r["split"], r["edit_type"]) for r in rows)
        bal = all(max(c[(s, sp, t)] for t in ("contradiction", "addition", "strengthening")) - min(c[(s, sp, t)] for t in ("contradiction", "addition", "strengthening")) <= 1
                  for s, sp in {(r["source"], r["split"]) for r in rows})
        check("setB_worksheet.csv: edit types balanced within source x split", bal)

# synthetic collision through label_tools export: each claim must get ITS OWN passage
with tempfile.TemporaryDirectory() as td:
    cols = ["source", "doc_id", "question_id", "qtype", "focus", "url", "question", "words", "passage_sha256", "status", "split", "passage"]
    srows = [dict.fromkeys(cols, "", ) | {"source": s, "question_id": "0000095-1", "question": f"Q for {s}", "passage": f"PASSAGE_{s}", "split": "test"}
             for s in ("NIDDK", "NHLBI")]
    crow = lambda s, n: {"claim_id": f"A-{s}-0000095-1-01", "question_id": qkey(s, "0000095-1"), "answer_id": "x", "set": "A", "source": s,
                         "split": "test", "generator": "g", "original_span": "", "char_start": "", "char_end": "", "claim_text": f"claim {n}", "edit_type": ""}
    for name, rows in (("sel.csv", srows), ("claims.csv", [crow("NIDDK", "niddk"), crow("NHLBI", "nhlbi")])):
        with open(os.path.join(td, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    r = subprocess.run([sys.executable, os.path.join(HERE, "label_tools.py"), "export", "--claims", os.path.join(td, "claims.csv"),
                        "--selected", os.path.join(td, "sel.csv"), "--split", "test", "--reviewers", "R1", "--out", os.path.join(td, "out")],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    if ok:
        form = rd(os.path.join(td, "out", "form_R1.csv"))
        ok = all(("niddk" in f["claim"]) == ("PASSAGE_NIDDK" == f["passage"]) and ("nhlbi" in f["claim"]) == ("PASSAGE_NHLBI" == f["passage"]) for f in form) and len(form) == 2
    check("label_tools export: colliding question ids get their own passages", ok, r.stderr[-200:])

sys.exit(1 if fails else 0)
