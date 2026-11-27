#!/usr/bin/env python3
"""Sensitivity analysis: restore the 17 refusal-type Set A claims excluded at the gold stage (Protocol Amendment 4).

Inputs : data/runs_excl17/{sampled_all,greedy_all}.jsonl (judge runs on the 17 claims), data/runs/{sampled_all,greedy_all}.jsonl,
         data/labels/gold.csv, data/labels/gold_excluded.csv (final_label_if_scored)
Output : data/results_exclusion.json  (descriptive counts and exact Clopper-Pearson intervals; the claims come from the same
         100 questions, so intervals ignore clustering and are descriptive)
"""
import json, sys, pandas as pd
from scipy.stats import beta
D = sys.argv[1] if len(sys.argv) > 1 else "data"
def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return float(lo), float(hi)
gold = pd.read_csv(f"{D}/labels/gold.csv"); ex = pd.read_csv(f"{D}/labels/gold_excluded.csv")
ex["y"] = (ex["final_label_if_scored"] == "unsupported").astype(int)
gA = gold[(gold["set"] == "A") & (gold["final_label"] != "unassessable")]
gA = gA.assign(y=(gA["final_label"] == "unsupported").astype(int))
yA = dict(zip(gA["claim_id"], gA["y"])); yE = dict(zip(ex["claim_id"], ex["y"]))
S = pd.concat([pd.read_json(f"{D}/runs/sampled_all.jsonl", lines=True), pd.read_json(f"{D}/runs_excl17/sampled_all.jsonl", lines=True)])
G = pd.concat([pd.read_json(f"{D}/runs/greedy_all.jsonl", lines=True), pd.read_json(f"{D}/runs_excl17/greedy_all.jsonl", lines=True)])
out = {"n_excluded": len(ex), "n_excluded_unsupported": int(ex["y"].sum()), "n_set_a_scored": len(gA), "n_set_a_unsupported": int(gA["y"].sum())}
for j in ["llama3_8b", "qwen25_7b"]:
    s = S[(S.judge_id == j)]; r = {}
    ref = s[(s.prompt_id == "P1") & (s.seed == 17)].set_index("claim_id")["parsed_label"]
    for name, ids, ymap in [("excluded17", list(yE), yE), ("setA_scored180", list(yA), yA), ("setA_restored197", list(yA) + list(yE), {**yA, **yE})]:
        pos = [c for c in ids if ymap[c] == 1]; neg = [c for c in ids if ymap[c] == 0]
        tp = sum(ref.get(c) == "UNSUPPORTED" for c in pos); fp = sum(ref.get(c) == "UNSUPPORTED" for c in neg)
        allsup = 0
        for c in pos:
            lab = s[s.claim_id == c]["parsed_label"]
            allsup += int(len(lab) == 9 and (lab == "SUPPORTED").all())
        r[name] = {"n_pos": len(pos), "tp": int(tp), "sens": tp / len(pos) if pos else None, "sens_ci": cp(int(tp), len(pos)) if pos else None,
                   "n_neg": len(neg), "fp": int(fp), "spec": 1 - fp / len(neg), "spec_ci": cp(len(neg) - int(fp), len(neg)),
                   "always_approved_unsupported": allsup}
    g = G[(G.judge_id == j)]
    r["greedy_restored197_per_prompt"] = {p: {"tp": int(sum((g[(g.prompt_id == p)].set_index("claim_id")["parsed_label"].get(c) == "UNSUPPORTED") for c in list(yA) + list(yE) if ({**yA, **yE})[c] == 1)),
                                              "n_pos": int(sum(({**yA, **yE})[c] for c in list(yA) + list(yE)))} for p in ["P1", "P2", "P3"]}
    inv = int(((S.judge_id == j) & S.claim_id.isin(list(yE)) & (S.status != "ok")).sum())
    r["invalid_on_excluded"] = inv
    out[j] = r
json.dump(out, open(f"{D}/results_exclusion.json", "w"), indent=1)
print(json.dumps(out, indent=1))
