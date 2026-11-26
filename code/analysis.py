#!/usr/bin/env python3
"""Detection and stability analysis for the MJAIH small-LM claim-judge study.

Inputs (frozen files):
  gold.csv   : claim_id, question_id, source, set, final_label
               final_label in {supported, unsupported, unassessable}
  runs.jsonl : claim_id, judge_id, prompt_id, seed, parsed_label, status
               parsed_label in {SUPPORTED, UNSUPPORTED} or null/invalid

Usage:
  python analysis.py --selftest
  python analysis.py --gold gold.csv --runs runs.jsonl --out results.json

Conventions: positive class = unsupported. Label cube L[claim, prompt, seed]
holds 1 (UNSUPPORTED), 0 (SUPPORTED) or -1 (invalid/missing). Reference
condition is prompt P1 (index 0) with seed 17 (index 0). All metrics take
per-claim weights so the same code serves the point estimate (w=1) and the
question-level stratified bootstrap (w = number of times the question is drawn).
"""
import argparse
import json
import itertools
import numpy as np
import pandas as pd

PROMPTS = ["P1", "P2", "P3"]
SEEDS = [17, 29, 43]
PAIRS = list(itertools.combinations(range(3), 2))  # (0,1),(0,2),(1,2)


def build_cubes(gold: pd.DataFrame, runs: pd.DataFrame, set_name: str, judge: str, keep_unassessable=False):
    """Return (claims_df, L) for one set and judge; missing rows are -1. Only sampled-arm rows are used
    (the greedy arm repeats seed 17 and would overwrite the reference cell)."""
    if "arm" in runs.columns:
        runs = runs[runs["arm"] == "sampled"]
    assert gold["claim_id"].is_unique, "duplicate claim_id in gold"
    g = gold[gold["set"] == set_name]
    if not keep_unassessable:
        g = g[g["final_label"] != "unassessable"]
    g = g.reset_index(drop=True)
    idx = {c: i for i, c in enumerate(g["claim_id"])}
    L = -np.ones((len(g), 3, 3), dtype=int)
    r = runs[(runs["judge_id"] == judge) & runs["claim_id"].isin(idx)]
    for row in r.itertuples():
        lab = row.parsed_label
        if row.status == "ok" and lab in ("SUPPORTED", "UNSUPPORTED"):
            L[idx[row.claim_id], PROMPTS.index(row.prompt_id), SEEDS.index(row.seed)] = int(lab == "UNSUPPORTED")
    return g, L


def _pair_counts(L, w, axis):
    """Weighted (disagree, valid, expected) over prompt pairs (axis='prompt') or seed pairs."""
    dis = val = exp = 0.0
    for a, b in PAIRS:
        for other in range(3):
            x, y = (L[:, a, other], L[:, b, other]) if axis == "prompt" else (L[:, other, a], L[:, other, b])
            ok = (x >= 0) & (y >= 0)
            dis += np.sum(w * (ok & (x != y)))
            val += np.sum(w * ok)
            exp += np.sum(w)
    return dis, val, exp


def disagreement(L, w, axis, mask=None):
    """Rate among valid pairs, plus bounds counting non-evaluable pairs as agree/disagree."""
    if mask is not None:
        L, w = L[mask], w[mask]
    dis, val, exp = _pair_counts(L, w, axis)
    nonval = exp - val
    return {
        "rate": dis / val if val else np.nan,
        "valid_pairs": val, "expected_pairs": exp,
        "lower_bound": dis / exp if exp else np.nan,
        "upper_bound": (dis + nonval) / exp if exp else np.nan,
    }


def detection(L, y, w):
    """Reference-condition metrics. y: 1 unsupported, 0 supported. Invalid = non-detection."""
    ref = L[:, 0, 0]
    pos, neg = y == 1, y == 0
    tp = np.sum(w * (pos & (ref == 1)))
    fn_valid = np.sum(w * (pos & (ref == 0)))
    inv_pos = np.sum(w * (pos & (ref < 0)))
    fp = np.sum(w * (neg & (ref == 1)))
    tn = np.sum(w * (neg & (ref == 0)))
    npos, nneg = np.sum(w * pos), np.sum(w * neg)
    prec = tp / (tp + fp) if tp + fp else np.nan
    rec_valid = tp / (tp + fn_valid) if tp + fn_valid else np.nan
    f1 = 2 * prec * rec_valid / (prec + rec_valid) if prec == prec and rec_valid == rec_valid and prec + rec_valid else np.nan
    return {
        "sensitivity": tp / npos if npos else np.nan,
        "specificity": tn / nneg if nneg else np.nan,
        "coverage": np.sum(w * (ref >= 0)) / np.sum(w),
        "tp": tp, "fn_valid": fn_valid, "invalid_unsupported": inv_pos,
        "precision_valid": prec, "f1_valid": f1,
        "n_unsupported": npos, "n_supported": nneg,
    }


def consistency(L, y, w):
    """Always-correct / always-wrong / mixed on claims with all nine calls valid."""
    full = (L >= 0).all(axis=(1, 2))
    correct = (L == y[:, None, None]).all(axis=(1, 2)) & full
    wrong = (L == (1 - y)[:, None, None]).all(axis=(1, 2)) & full
    mixed = full & ~correct & ~wrong
    out = {k: float(np.sum(w * v)) for k, v in dict(always_correct=correct, always_wrong=wrong, mixed=mixed).items()}
    out["claims_all_valid"] = float(np.sum(w * full))
    pos = y == 1
    out["unsupported_always_approved"] = float(np.sum(w * (wrong & pos)))
    return out


def summarize(L, y, w):
    return {
        "detection": detection(L, y, w),
        "prompt_disagreement": disagreement(L, w, "prompt"),
        "seed_disagreement": disagreement(L, w, "seed"),
        "prompt_disagreement_gold_unsupported": disagreement(L, w, "prompt", y == 1),
        "prompt_disagreement_gold_supported": disagreement(L, w, "prompt", y == 0),
        "seed_disagreement_gold_unsupported": disagreement(L, w, "seed", y == 1),
        "seed_disagreement_gold_supported": disagreement(L, w, "seed", y == 0),
        "consistency": consistency(L, y, w),
    }


def bootstrap(claims, cubes, B=2000, seed=20261124):
    """Paired bootstrap. Resample whole questions with replacement within source strata;
    every judge's cube shares the same weights, so between-judge differences are paired.
    cubes: {judge: L}. Returns {metric_name: {judge or 'diff': (lo, hi, n_defined)}}."""
    rng = np.random.default_rng(seed)
    y = (claims["final_label"] == "unsupported").astype(int).to_numpy()
    q_of_claim = claims["question_id"].to_numpy()
    questions = claims.drop_duplicates("question_id")[["question_id", "source"]]
    judges = list(cubes)
    draws = {j: [] for j in judges}
    diffs = []
    for _ in range(B):
        qw = {}
        for _, grp in questions.groupby("source"):
            ids = grp["question_id"].to_numpy()
            pick = rng.choice(ids, size=len(ids), replace=True)
            for q, c in zip(*np.unique(pick, return_counts=True)):
                qw[q] = c
        w = np.array([qw.get(q, 0) for q in q_of_claim], dtype=float)
        flat = {}
        for j in judges:
            s = summarize(cubes[j], y, w)
            flat[j] = {
                "sensitivity": s["detection"]["sensitivity"],
                "specificity": s["detection"]["specificity"],
                "prompt_disagreement": s["prompt_disagreement"]["rate"],
                "seed_disagreement": s["seed_disagreement"]["rate"],
            }
            draws[j].append(flat[j])
        if len(judges) == 2:
            a, b = judges
            diffs.append({k: flat[a][k] - flat[b][k] for k in flat[a]})
    out = {}
    for name, rows in list(draws.items()) + ([("diff", diffs)] if diffs else []):
        df = pd.DataFrame(rows)
        out[name] = {c: (float(np.nanpercentile(df[c], 2.5)) if df[c].notna().any() else None,
                         float(np.nanpercentile(df[c], 97.5)) if df[c].notna().any() else None,
                         int(df[c].notna().sum())) for c in df.columns}
    return out


def greedy_summary(gold, greedy, set_name, judge):
    """Greedy arm (temperature 0, one run per prompt): per-prompt detection and prompt disagreement."""
    g = gold[(gold["set"] == set_name) & (gold["final_label"] != "unassessable")].reset_index(drop=True)
    idx = {c: i for i, c in enumerate(g["claim_id"])}
    y = (g["final_label"] == "unsupported").astype(int).to_numpy()
    G = -np.ones((len(g), 3), dtype=int)
    for row in greedy[(greedy["judge_id"] == judge) & greedy["claim_id"].isin(idx)].itertuples():
        if row.status == "ok" and row.parsed_label in ("SUPPORTED", "UNSUPPORTED"):
            G[idx[row.claim_id], PROMPTS.index(row.prompt_id)] = int(row.parsed_label == "UNSUPPORTED")
    out = {"per_prompt": {}}
    for k, pid in enumerate(PROMPTS):
        v = G[:, k]
        pos, neg = y == 1, y == 0
        out["per_prompt"][pid] = {"sensitivity": float(np.sum(pos & (v == 1)) / max(pos.sum(), 1)),
                                  "specificity": float(np.sum(neg & (v == 0)) / max(neg.sum(), 1)),
                                  "coverage": float(np.mean(v >= 0)), "n_unsupported": int(pos.sum()), "n_supported": int(neg.sum())}
    dis = val = 0
    for a, b in PAIRS:
        ok = (G[:, a] >= 0) & (G[:, b] >= 0)
        dis += int(np.sum(ok & (G[:, a] != G[:, b]))); val += int(ok.sum())
    out["prompt_disagreement"] = {"rate": dis / val if val else None, "disagree": dis, "valid_pairs": val}
    return out


def self_cross(claims, L, y):
    """Prespecified stratification (Set A): judge is the generator of the answer (self) or the other model (cross)."""
    res = {}
    for name, mask in (("self", claims["_self"].to_numpy()), ("cross", ~claims["_self"].to_numpy())):
        w = mask.astype(float)
        res[name] = {"n_claims": int(mask.sum()), "detection": detection(L, y, w),
                     "prompt_disagreement": disagreement(L, w, "prompt"), "seed_disagreement": disagreement(L, w, "seed")}
    return res


def unassessable_sensitivity(gold, runs, set_name, judge):
    """Add unassessable claims to the denominator first as supported (0), then as unsupported (1)."""
    claims, L = build_cubes(gold, runs, set_name, judge, keep_unassessable=True)
    out = {}
    for name, fill in (("as_supported", 0), ("as_unsupported", 1)):
        y = np.where(claims["final_label"] == "unassessable", fill, (claims["final_label"] == "unsupported").astype(int)).astype(int)
        w = np.ones(len(claims))
        d = detection(L, y, w)
        out[name] = {"n_unassessable": int((claims["final_label"] == "unassessable").sum()),
                     "sensitivity": d["sensitivity"], "specificity": d["specificity"],
                     "n_unsupported": d["n_unsupported"], "n_supported": d["n_supported"]}
    return out


def run_all(gold, runs, B=2000, greedy=None):
    results = {}
    for set_name in sorted(gold["set"].unique()):
        judges = sorted(runs["judge_id"].unique())
        claims, cubes = None, {}
        for j in judges:
            claims, cubes[j] = build_cubes(gold, runs, set_name, j)
        y = (claims["final_label"] == "unsupported").astype(int).to_numpy()
        w = np.ones(len(claims))
        results[set_name] = {
            "point": {j: summarize(cubes[j], y, w) for j in judges},
            "bootstrap_95ci": bootstrap(claims, cubes, B=B),
            "unassessable_sensitivity": {j: unassessable_sensitivity(gold, runs, set_name, j) for j in judges},
        }
        if "generator" in claims.columns and (claims["generator"].astype(str).str.len() > 0).any():
            results[set_name]["self_vs_cross"] = {}
            for j in judges:
                c2 = claims.copy(); c2["_self"] = (c2["generator"] == j)
                results[set_name]["self_vs_cross"][j] = self_cross(c2, cubes[j], y)
        if greedy is not None:
            results[set_name]["greedy"] = {j: greedy_summary(gold, greedy, set_name, j) for j in judges}
    return results


# ----------------------------------------------------------------------------
# Hand-checked example: one unsupported miss (invalid reference response),
# one prompt flip, one always-correct supported claim. Expected values are
# derived by hand in the comments and asserted below.
# ----------------------------------------------------------------------------
def selftest():
    S, U, X = 0, 1, -1
    c1 = np.full((3, 3), U); c1[1, 0] = S          # gold unsupported; P2 at seed 17 flips to SUPPORTED
    c2 = np.full((3, 3), S); c2[0, 0] = X          # gold unsupported; reference call invalid, otherwise SUPPORTED
    c3 = np.full((3, 3), S)                        # gold supported; always correct
    L = np.stack([c1, c2, c3])
    y = np.array([1, 1, 0]); w = np.ones(3)

    d = detection(L, y, w)
    assert d["sensitivity"] == 0.5                 # c1 detected, c2 invalid counts as a miss: 1/2
    assert d["specificity"] == 1.0                 # c3 approved: 1/1
    assert abs(d["coverage"] - 2 / 3) < 1e-12      # c2 reference call invalid
    assert d["precision_valid"] == 1.0 and d["f1_valid"] == 1.0
    assert d["invalid_unsupported"] == 1

    p = disagreement(L, w, "prompt")
    # c1: seed 17 labels U,S,U -> 2 disagreements of 3 pairs; other seeds 0 of 3 -> 2/9 valid
    # c2: 9 expected, 2 pairs non-evaluable (P1 at seed 17) -> 7 valid, 0 disagree
    # c3: 0 of 9.  Total: 2 disagree / 25 valid, expected 27
    assert p["valid_pairs"] == 25 and p["expected_pairs"] == 27
    assert abs(p["rate"] - 2 / 25) < 1e-12
    assert abs(p["lower_bound"] - 2 / 27) < 1e-12 and abs(p["upper_bound"] - 4 / 27) < 1e-12

    s = disagreement(L, w, "seed")
    # c1: P2 labels S,U,U across seeds -> 2 of 3 seed pairs differ; c2 invalid cell removes 2 pairs
    assert s["valid_pairs"] == 25 and abs(s["rate"] - 2 / 25) < 1e-12

    c = consistency(L, y, w)
    assert c["claims_all_valid"] == 2 and c["always_correct"] == 1 and c["mixed"] == 1
    assert c["always_wrong"] == 0 and c["unsupported_always_approved"] == 0

    # Resampling logic: weights of 2 on c1 and 0 on c2 must reproduce c1's own numbers.
    w2 = np.array([2.0, 0.0, 1.0])
    d2 = detection(L, y, w2)
    assert d2["sensitivity"] == 1.0                # only c1 carries unsupported weight
    print("selftest passed: detection, prompt/seed disagreement, bounds, consistency, weighting")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--gold"); ap.add_argument("--runs"); ap.add_argument("--out", default="results.json")
    ap.add_argument("--greedy", help="runs file from the greedy arm (optional)")
    ap.add_argument("--B", type=int, default=2000)
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        gold = pd.read_csv(a.gold)
        runs = pd.read_json(a.runs, lines=True)
        greedy = pd.read_json(a.greedy, lines=True) if a.greedy else None
        res = run_all(gold, runs, B=a.B, greedy=greedy)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=2, default=float)
        print("wrote", a.out)
