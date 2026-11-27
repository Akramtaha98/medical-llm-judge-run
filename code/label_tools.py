#!/usr/bin/env python3
"""Blinded labelling, agreement, adjudication and gold labels. No judge output is read here.

  1. export   python code/label_tools.py export --claims data/claims/claims_A.csv data/claims/claims_B.csv \
                  --selected data/corpus/selected.csv --split test --reviewers R1 R2 --out data/labels
        -> claim_key.csv (blind_id -> claim_id; keep away from reviewers), form_R1.csv, form_R2.csv
        Reviewers see only blind_id, question, passage, claim. Rows are shuffled differently per reviewer and
        the two members of a Set B pair are never adjacent. Generator, set, edit type and the other label are absent.
  2. (reviewers fill label in {supported, unsupported, unassessable}, subtype, evidence_span, reason)
  3. agree    python code/label_tools.py agree --forms data/labels/form_R1.csv data/labels/form_R2.csv --out data/labels
        -> agreement.json (raw agreement, Cohen's kappa) and adjudication_sheet.csv (only disagreements, labels hidden)
  4. (third reviewer fills final_label, subtype, adjudication_note in the sheet)
  5. gold     python code/label_tools.py gold --forms ... --adjudicated data/labels/adjudication_sheet.csv \
                  --key data/labels/claim_key.csv --claims data/claims/claims_A.csv data/claims/claims_B.csv --out data/labels
        -> gold.csv and yield.json (unsupported counts BEFORE any judge output; minimum-yield rule check)
"""
import argparse, csv, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qkeys import qkey, assert_unique
from collections import Counter

LABELS = ["supported", "unsupported", "unassessable"]


def read_csv(p):
    return list(csv.DictReader(open(p, newline="", encoding="utf-8")))


def write_csv(p, rows, fields=None):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0])); w.writeheader(); w.writerows(rows)


def load_claims(paths, split=None):
    rows = [r for p in paths for r in read_csv(p)]
    return [r for r in rows if split in (None, "all") or r["split"] == split]


def separate_pairs(order, qid_of):
    """Shuffle fix: no two consecutive rows share a question (separates matched variants)."""
    for i in range(1, len(order)):
        if qid_of[order[i]] == qid_of[order[i - 1]]:
            for j in range(i + 1, len(order)):
                if qid_of[order[j]] != qid_of[order[i - 1]]:
                    order[i], order[j] = order[j], order[i]; break
    return order


def export(claims_paths, selected, split, reviewers, outdir, seed=2026):
    claims = load_claims(claims_paths, split)
    sel_rows = read_csv(selected)
    assert_unique([qkey(r["source"], r["question_id"]) for r in sel_rows], "(source, question_id) in selected.csv")
    sel = {qkey(r["source"], r["question_id"]): r for r in sel_rows}
    assert_unique([c["claim_id"] for c in claims], "claim_id in claims files")
    lost = [c["claim_id"] for c in claims if c["question_id"] not in sel]
    if lost:
        sys.exit(f"{len(lost)} claims point to a question key not in selected.csv (first: {lost[0]})")
    wrong = [c["claim_id"] for c in claims if sel[c["question_id"]]["source"] != c["source"]]
    if wrong:
        sys.exit(f"{len(wrong)} claims have a source that differs from selected.csv (first: {wrong[0]})")
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(seed)
    ids = rng.sample(range(100000, 1000000), len(claims))
    key = [{"blind_id": f"I{b}", "claim_id": c["claim_id"]} for b, c in zip(ids, claims)]
    write_csv(os.path.join(outdir, "claim_key.csv"), key)
    by_blind = {k["blind_id"]: c for k, c in zip(key, claims)}
    for rv in reviewers:
        rr = random.Random(f"{seed}-{rv}")
        order = [k["blind_id"] for k in key]; rr.shuffle(order)
        order = separate_pairs(order, {b: c["question_id"] for b, c in by_blind.items()})
        rows = [{"blind_id": b, "question": sel[by_blind[b]["question_id"]]["question"],
                 "passage": sel[by_blind[b]["question_id"]]["passage"], "claim": by_blind[b]["claim_text"],
                 "label": "", "subtype": "", "evidence_span": "", "reason": ""} for b in order]
        write_csv(os.path.join(outdir, f"form_{rv}.csv"), rows)
    print(f"{len(claims)} claims -> {len(reviewers)} blinded forms + claim_key.csv in {outdir}")


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[l] * cb[l] for l in LABELS) / n ** 2
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def load_forms(paths):
    forms = []
    for p in paths:
        rows = {r["blind_id"]: r for r in read_csv(p)}
        bad = [b for b, r in rows.items() if r["label"].strip().lower() not in LABELS]
        if bad:
            sys.exit(f"{p}: {len(bad)} rows without a valid label (first: {bad[0]}); allowed {LABELS}")
        forms.append(rows)
    return forms


def agree(form_paths, outdir):
    forms = load_forms(form_paths)
    if len(forms) != 2:
        sys.exit("agreement needs exactly two reviewer forms")
    f1, f2 = forms
    ids = sorted(f1)
    if set(f1) != set(f2):
        sys.exit("the two forms cover different items")
    a = [f1[i]["label"].strip().lower() for i in ids]; b = [f2[i]["label"].strip().lower() for i in ids]
    po, k = kappa(a, b)
    rep = {"n_items": len(ids), "raw_agreement": po, "cohens_kappa": k, "n_disagreements": sum(x != y for x, y in zip(a, b)),
           "label_counts_reviewer1": dict(Counter(a)), "label_counts_reviewer2": dict(Counter(b))}
    json.dump(rep, open(os.path.join(outdir, "agreement.json"), "w"), indent=2)
    dis = [{"blind_id": i, "question": f1[i]["question"], "passage": f1[i]["passage"], "claim": f1[i]["claim"],
            "final_label": "", "subtype": "", "adjudication_note": ""} for i, x, y in zip(ids, a, b) if x != y]
    if dis:
        write_csv(os.path.join(outdir, "adjudication_sheet.csv"), dis)
    print(json.dumps(rep, indent=2)); print(f"{len(dis)} items sent to adjudication")


def gold(form_paths, adj_path, key_path, claims_paths, outdir, min_yield=30, split="test", exclude_path=None):
    f1, f2 = load_forms(form_paths)
    adj = {r["blind_id"]: r for r in read_csv(adj_path)} if adj_path and os.path.exists(adj_path) else {}
    key = {r["blind_id"]: r["claim_id"] for r in read_csv(key_path)}
    claims = {c["claim_id"]: c for c in load_claims(claims_paths, split)}
    excl_ids = {r["claim_id"] for r in read_csv(exclude_path)} if exclude_path else set()
    unknown = excl_ids - set(key.values())
    if unknown:
        sys.exit(f"excluded claim ids not in key: {sorted(unknown)[:3]}")
    out, excluded = [], []
    for b, cid in key.items():
        l1, l2 = f1[b]["label"].strip().lower(), f2[b]["label"].strip().lower()
        sub, note, excl = f1[b]["subtype"], "", ""
        if l1 == l2:
            final = l1
        else:
            a = adj.get(b)
            if not a or a["final_label"].strip().lower() not in LABELS:
                sys.exit(f"{b} ({cid}) disagreed and has no adjudicated final_label")
            final, sub, note = a["final_label"].strip().lower(), a["subtype"], a["adjudication_note"]
        c = claims[cid]
        if cid in excl_ids:
            excluded.append({"claim_id": cid, "final_label_if_scored": final, "reviewer1": l1, "reviewer2": l2})
            continue
        out.append({"claim_id": cid, "question_id": c["question_id"], "source": c["source"], "set": c["set"],
                    "generator": c["generator"], "edit_type": c["edit_type"], "final_label": final, "subtype": sub,
                    "adjudication_note": note, "exclusion_reason": "unassessable" if final == "unassessable" else ""})
    write_csv(os.path.join(outdir, "gold.csv"), out)
    if excluded:
        write_csv(os.path.join(outdir, "gold_excluded.csv"), excluded)
    cnt = Counter((r["set"], r["final_label"]) for r in out)
    nu_a = cnt[("A", "unsupported")]
    rep = {"n_excluded_refusal": len(excluded), "counts": {f"{s}:{l}": n for (s, l), n in sorted(cnt.items())}, "set_A_unsupported": nu_a, "minimum_yield": min_yield,
           "minimum_yield_met": nu_a >= min_yield,
           "action": "proceed to judge runs" if nu_a >= min_yield else
                     f"Set A has {nu_a} unsupported claims (< {min_yield}): draw more questions in order from data/corpus/reserve.csv and process identically BEFORE any judge output is examined"}
    json.dump(rep, open(os.path.join(outdir, "yield.json"), "w"), indent=2)
    print(json.dumps(rep, indent=2)); print(f"gold.csv: {len(out)} rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "agree", "gold"])
    ap.add_argument("--claims", nargs="+"); ap.add_argument("--selected", default="data/corpus/selected.csv")
    ap.add_argument("--split", default="test"); ap.add_argument("--reviewers", nargs="+", default=["R1", "R2"])
    ap.add_argument("--forms", nargs="+"); ap.add_argument("--adjudicated"); ap.add_argument("--key", default="data/labels/claim_key.csv")
    ap.add_argument("--min-yield", type=int, default=30); ap.add_argument("--exclude"); ap.add_argument("--out", default="data/labels")
    a = ap.parse_args()
    if a.cmd == "export": export(a.claims, a.selected, a.split, a.reviewers, a.out)
    elif a.cmd == "agree": agree(a.forms, a.out)
    else: gold(a.forms, a.adjudicated, a.key, a.claims, a.out, a.min_yield, a.split, a.exclude)
