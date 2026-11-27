#!/usr/bin/env python3
"""Exploratory and reporting analyses that analysis.py does not produce. Added after the freeze; it changes no
frozen file and reads only gold.csv, the two frozen run files and items.csv. Same paired question-level
bootstrap (2,000 draws, strata = source, seed 20261124) as analysis.py.

  python code/analysis_extra.py --gold data/labels/gold.csv --runs data/runs/sampled_all.jsonl \
      --greedy data/runs/greedy_all.jsonl --items data/items.csv --out data/results_extra.json --misses data/misses.csv

Outputs (a) subgroup sensitivity by edit type and by reviewer subtype with CIs and the share approved under all nine
conditions, (b) disagreement by gold class with CIs, (c) greedy-arm sensitivity and prompt disagreement with CIs,
(d) sensitivity range over the nine sampled conditions, (e) overlap of the two judges' misses, (f) always-supported
and always-unsupported rule accuracy, (g) a CSV of every claim a judge got wrong in the reference condition."""
import argparse, json, sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import analysis as A

J = ["llama3_8b", "qwen25_7b"]


def greedy_matrix(gold, greedy, set_name, judge):
    g = gold[(gold["set"] == set_name) & (gold["final_label"] != "unassessable")].reset_index(drop=True)
    idx = {c: i for i, c in enumerate(g["claim_id"])}
    G = -np.ones((len(g), 3), dtype=int)
    for r in greedy[(greedy["judge_id"] == judge) & greedy["claim_id"].isin(idx)].itertuples():
        if r.status == "ok" and r.parsed_label in ("SUPPORTED", "UNSUPPORTED"):
            G[idx[r.claim_id], A.PROMPTS.index(r.prompt_id)] = int(r.parsed_label == "UNSUPPORTED")
    return g, G


def sens(L, y, w, mask=None):
    m = (y == 1) if mask is None else ((y == 1) & mask)
    den = np.sum(w * m)
    return np.sum(w * (m & (L[:, 0, 0] == 1))) / den if den else np.nan


def always_approved(L, y, w, mask):
    m = (y == 1) & mask
    full = (L >= 0).all(axis=(1, 2))
    wrong = (L == 0).all(axis=(1, 2)) & full
    den = np.sum(w * m)
    return np.sum(w * (m & wrong)) / den if den else np.nan


def pct(v):
    v = np.asarray(v, dtype=float)
    if np.isnan(v).all():
        return [None, None, 0]
    return [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5)), int((~np.isnan(v)).sum())]


def boot(claims, fn, B, seed=20261124):
    """fn(w) -> {name: value}. Returns {name: [lo, hi, n_defined]} over question-level stratified draws."""
    rng = np.random.default_rng(seed)
    qs = claims.drop_duplicates("question_id")[["question_id", "source"]]
    qc = claims["question_id"].to_numpy()
    draws = []
    for _ in range(B):
        qw = {}
        for _, grp in qs.groupby("source"):
            ids = grp["question_id"].to_numpy()
            for q, c in zip(*np.unique(rng.choice(ids, size=len(ids), replace=True), return_counts=True)):
                qw[q] = c
        draws.append(fn(np.array([qw.get(q, 0) for q in qc], dtype=float)))
    df = pd.DataFrame(draws)
    return {c: pct(df[c]) for c in df.columns}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold"); ap.add_argument("--runs"); ap.add_argument("--greedy"); ap.add_argument("--items")
    ap.add_argument("--out"); ap.add_argument("--misses"); ap.add_argument("--B", type=int, default=2000)
    a = ap.parse_args()
    gold = pd.read_csv(a.gold); runs = pd.read_json(a.runs, lines=True); greedy = pd.read_json(a.greedy, lines=True)
    items = pd.read_csv(a.items).set_index("claim_id")
    out = {}
    miss_rows = []
    for S in ["A", "B"]:
        cubes, claims = {}, None
        for j in J:
            claims, cubes[j] = A.build_cubes(gold, runs, S, j)
        y = (claims["final_label"] == "unsupported").astype(int).to_numpy()
        n = len(claims)
        et = claims["edit_type"].fillna("").to_numpy(); st = claims["subtype"].fillna("").to_numpy()
        groups = {"all_unsupported": y == 1}
        for k in ["addition", "contradiction", "strengthening"]:
            if (et == k).any(): groups[f"edit:{k}"] = (et == k) & (y == 1)
        for k in ["contradicted", "absent_or_overextended"]:
            if (st == k).any(): groups[f"subtype:{k}"] = (st == k) & (y == 1)
        res = {"n_claims": n, "groups": {}, "disagreement_by_class": {}, "sens_range_9": {}, "greedy": {}}
        # (a) subgroup sensitivity + share approved under all nine conditions
        w1 = np.ones(n)
        for gname, mask in groups.items():
            ent = {"n": int(mask.sum())}
            for j in J:
                ent[j] = {"sensitivity": float(sens(cubes[j], y, w1, mask)),
                          "always_approved": float(always_approved(cubes[j], y, w1, mask)),
                          "missed_ref": int(np.sum(mask & (cubes[j][:, 0, 0] == 0)))}
            def fn(w, mask=mask):
                d = {}
                for j in J:
                    d[f"{j}_sens"] = sens(cubes[j], y, w, mask)
                    d[f"{j}_always"] = always_approved(cubes[j], y, w, mask)
                d["diff_sens"] = d[f"{J[0]}_sens"] - d[f"{J[1]}_sens"]
                return d
            ent["ci"] = boot(claims, fn, a.B)
            res["groups"][gname] = ent
        # (b) disagreement by gold class with CIs
        def fn_dis(w):
            d = {}
            for j in J:
                for fac in ("prompt", "seed"):
                    for cls, m in (("unsupported", y == 1), ("supported", y == 0)):
                        d[f"{j}_{fac}_{cls}"] = A.disagreement(cubes[j], w, fac, m)["rate"]
            return d
        res["disagreement_by_class"] = {"point": {f"{j}_{fac}_{cls}": A.disagreement(cubes[j], w1, fac, m)["rate"]
                                                   for j in J for fac in ("prompt", "seed")
                                                   for cls, m in (("unsupported", y == 1), ("supported", y == 0))},
                                        "ci": boot(claims, fn_dis, a.B)}
        # (d) sensitivity over the nine sampled conditions (unsupported claims, valid output only)
        for j in J:
            vals = []
            for p in range(3):
                for s in range(3):
                    pos = y == 1
                    vals.append(float(np.sum(pos & (cubes[j][:, p, s] == 1)) / max(pos.sum(), 1)))
            res["sens_range_9"][j] = {"min": min(vals), "max": max(vals), "mean": float(np.mean(vals)), "per_condition": vals}
        # (c) greedy arm with CIs: pooled over the three prompts
        Gm = {}
        for j in J:
            gg, Gm[j] = greedy_matrix(gold, greedy, S, j)
            assert list(gg["claim_id"]) == list(claims["claim_id"])
        def gsens(G, w):
            pos = y == 1
            return float(np.mean([np.sum(w * (pos & (G[:, k] == 1))) / np.sum(w * pos) for k in range(3)]))
        def gdis(G, w):
            dis = val = 0.0
            for p1, p2 in A.PAIRS:
                ok = (G[:, p1] >= 0) & (G[:, p2] >= 0)
                dis += np.sum(w * (ok & (G[:, p1] != G[:, p2]))); val += np.sum(w * ok)
            return dis / val if val else np.nan
        def fn_g(w):
            d = {}
            for j in J:
                d[f"{j}_sens"] = gsens(Gm[j], w); d[f"{j}_dis"] = gdis(Gm[j], w)
            return d
        res["greedy"] = {"point": {j: {"sensitivity_pooled": gsens(Gm[j], w1), "prompt_disagreement": gdis(Gm[j], w1),
                                       "disagree_pairs": int(round(gdis(Gm[j], w1) * 3 * n)), "valid_pairs": 3 * n} for j in J},
                         "ci": boot(claims, fn_g, a.B)}
        # (e) overlap of misses (reference and all-nine)
        pos = y == 1
        m_ref = {j: pos & (cubes[j][:, 0, 0] == 0) for j in J}
        m_all = {j: pos & (cubes[j] == 0).all(axis=(1, 2)) for j in J}
        res["miss_overlap"] = {"ref_both": int(np.sum(m_ref[J[0]] & m_ref[J[1]])), "ref_llama_only": int(np.sum(m_ref[J[0]] & ~m_ref[J[1]])),
                               "ref_qwen_only": int(np.sum(~m_ref[J[0]] & m_ref[J[1]])), "ref_neither": int(np.sum(pos & ~m_ref[J[0]] & ~m_ref[J[1]])),
                               "all9_both": int(np.sum(m_all[J[0]] & m_all[J[1]])), "all9_llama": int(m_all[J[0]].sum()), "all9_qwen": int(m_all[J[1]].sum())}
        # (f) rule accuracy
        res["rules"] = {"always_supported_accuracy": float(np.mean(y == 0)), "always_unsupported_accuracy": float(np.mean(y == 1))}
        # (g) misses and false alarms at the reference condition
        for i in range(n):
            wrong = [j for j in J if cubes[j][i, 0, 0] != y[i]]
            if wrong:
                cid = claims["claim_id"].iloc[i]
                miss_rows.append({"claim_id": cid, "set": S, "source": claims["source"].iloc[i], "generator": claims["generator"].iloc[i] if S == "A" else "",
                                  "gold": claims["final_label"].iloc[i], "edit_type": claims["edit_type"].iloc[i], "subtype": claims["subtype"].iloc[i],
                                  "wrong_judges": ";".join(wrong),
                                  "llama_unsup_of_9": int(cubes[J[0]][i].sum()), "qwen_unsup_of_9": int(cubes[J[1]][i].sum()),
                                  "claim": items.loc[cid, "claim"] if cid in items.index else ""})
        out[S] = res
    pd.DataFrame(miss_rows).to_csv(a.misses, index=False)
    json.dump(out, open(a.out, "w"), indent=2, default=float)
    print("wrote", a.out, a.misses, len(miss_rows), "reference-condition errors")


if __name__ == "__main__":
    main()
