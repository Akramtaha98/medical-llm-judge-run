#!/usr/bin/env python3
"""Set B controlled pairs: worksheet for the person who writes the edits, then ingest.

The edits MUST be written by someone other than the reference reviewers. This script writes no claim text.

  python code/make_setB.py worksheet --selected data/corpus/selected.csv --out data/claims
      -> data/claims/setB_worksheet.csv  (one row per question; edit_type assigned in a balanced, seeded rotation)
  (human fills supported_paraphrase and edited_claim for every row; both must be checkable against the passage only)
  python code/make_setB.py ingest --worksheet data/claims/setB_worksheet.csv --out data/claims
      -> data/claims/claims_B.csv  (two claims per question: B-<qid>-S supported paraphrase, B-<qid>-E edited claim)

Edit types: contradiction (passage says the opposite), addition (plausible detail absent from the passage),
strengthening (stronger certainty or wider population than the passage supports).
"""
import argparse, csv, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qkeys import qkey, assert_unique
from collections import defaultdict

TYPES = ["contradiction", "addition", "strengthening"]


def worksheet(selected, outdir, seed=2026):
    rows = list(csv.DictReader(open(selected, newline="", encoding="utf-8")))
    rng = random.Random(seed)
    by_src = defaultdict(list)
    for r in rows:
        by_src[(r["source"], r["split"])].append(r)
    out = []
    for k in sorted(by_src):  # rotate edit types within source x split so each type is balanced
        grp = sorted(by_src[k], key=lambda r: r["question_id"]); rng.shuffle(grp)
        offset = rng.randrange(3)
        for i, r in enumerate(grp):
            out.append({"question_id": qkey(r["source"], r["question_id"]), "source": r["source"], "split": r["split"],
                        "question": r["question"], "passage": r["passage"], "edit_type": TYPES[(i + offset) % 3],
                        "edited_first": int(rng.random() < 0.5), "supported_paraphrase": "", "edited_claim": "", "builder_note": ""})
    out.sort(key=lambda r: (r["question_id"].split("-", 1)[1], r["source"]))
    assert_unique([r["question_id"] for r in out], "question key in worksheet")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "setB_worksheet.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    cnt = defaultdict(int)
    for r in out:
        cnt[(r["split"], r["edit_type"])] += 1
    print(f"{len(out)} rows -> {path}"); print(dict(cnt))


def ingest(ws_path, outdir):
    rows = list(csv.DictReader(open(ws_path, newline="", encoding="utf-8")))
    assert_unique([r["question_id"] for r in rows], "question key in worksheet")
    bad = [r["question_id"] for r in rows if not r["supported_paraphrase"].strip() or not r["edited_claim"].strip()]
    if bad:
        sys.exit(f"{len(bad)} rows incomplete (first: {bad[0]})")
    same = [r["question_id"] for r in rows if r["supported_paraphrase"].strip().lower() == r["edited_claim"].strip().lower()]
    if same:
        sys.exit(f"edited claim identical to paraphrase: {same[:3]}")
    out = []
    for r in rows:
        for tag, col, typ in (("S", "supported_paraphrase", ""), ("E", "edited_claim", r["edit_type"])):
            out.append({"claim_id": f"B-{r['question_id']}-{tag}", "question_id": r["question_id"], "answer_id": f"pair-{r['question_id']}",
                        "set": "B", "source": r["source"], "split": r["split"], "generator": "", "original_span": "",
                        "char_start": "", "char_end": "", "claim_text": r[col].strip(), "edit_type": typ})
    assert_unique([o["claim_id"] for o in out], "Set B claim_id")
    path = os.path.join(outdir, "claims_B.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"{len(out)} Set B claims ({len(rows)} pairs) -> {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["worksheet", "ingest"])
    ap.add_argument("--selected", default="data/corpus/selected.csv"); ap.add_argument("--worksheet", default="data/claims/setB_worksheet.csv")
    ap.add_argument("--out", default="data/claims")
    a = ap.parse_args()
    worksheet(a.selected, a.out) if a.cmd == "worksheet" else ingest(a.worksheet, a.out)
