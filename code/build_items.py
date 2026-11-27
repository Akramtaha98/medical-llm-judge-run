#!/usr/bin/env python3
"""Build the frozen judge input items.csv from adjudicated claims.

  python code/build_items.py --gold data/labels/gold.csv --claims data/claims/claims_A.csv data/claims/claims_B.csv \
      --selected data/corpus/selected.csv --out data/items.csv

items.csv columns: claim_id, question_id, question, passage, claim. Unassessable claims are kept (needed for the
prespecified sensitivity analysis); analysis.py excludes them from the primary denominator. gold.csv is copied
unchanged in meaning to the analysis input, so run analysis with --gold data/labels/gold.csv.
"""
import argparse, csv, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qkeys import qkey, assert_unique


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True); ap.add_argument("--claims", nargs="+", required=True)
    ap.add_argument("--selected", default="data/corpus/selected.csv"); ap.add_argument("--out", default="data/items.csv")
    a = ap.parse_args()
    rd = lambda p: list(csv.DictReader(open(p, newline="", encoding="utf-8")))
    gold = rd(a.gold); sel_rows = rd(a.selected)
    assert_unique([qkey(r["source"], r["question_id"]) for r in sel_rows], "(source, question_id) in selected.csv")
    sel = {qkey(r["source"], r["question_id"]): r for r in sel_rows}
    assert_unique([g["claim_id"] for g in gold], "claim_id in gold")
    claims = {c["claim_id"]: c for p in a.claims for c in rd(p)}
    rows = []
    for g in gold:
        if g["exclusion_reason"] not in ("", "unassessable"):
            continue
        c = claims[g["claim_id"]]; q = sel[c["question_id"]]
        rows.append({"claim_id": g["claim_id"], "question_id": c["question_id"], "question": q["question"],
                     "passage": q["passage"], "claim": c["claim_text"]})
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    sha = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    print(f"{len(rows)} items -> {a.out}\nsha256 {sha}  (record in the protocol freeze)")


if __name__ == "__main__":
    main()
