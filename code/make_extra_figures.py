#!/usr/bin/env python3
"""Figures from results.json and results_extra.json (locked study data only).
  python code/make_extra_figures.py data/results.json data/results_extra.json writing/3_source
Writes fig_stability_class.png (Figure 4: prompt and seed disagreement by judge, set and gold class, 95% bootstrap CI)
and fig_errortype.png (Figure 5: Set B sensitivity by edit type, 95% bootstrap CI)."""
import json, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

J = ["llama3_8b", "qwen25_7b"]; NAME = {"llama3_8b": "Llama 3 8B", "qwen25_7b": "Qwen2.5 7B"}
COL = {"llama3_8b": "#0072B2", "qwen25_7b": "#E69F00"}


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def stability(ext, path):
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.5), sharey=True)
    cats = [("prompt", "supported"), ("prompt", "unsupported"), ("seed", "supported"), ("seed", "unsupported")]
    labels = ["Prompt\nsupported", "Prompt\nunsupported", "Seed\nsupported", "Seed\nunsupported"]
    for ax, S in zip(axs, ["A", "B"]):
        d = ext[S]["disagreement_by_class"]; x = np.arange(len(cats)); w = 0.36
        for k, j in enumerate(J):
            pts = np.array([d["point"][f"{j}_{f}_{c}"] for f, c in cats], dtype=float)
            lo = np.array([d["ci"][f"{j}_{f}_{c}"][0] if d["ci"][f"{j}_{f}_{c}"][0] is not None else p for (f, c), p in zip(cats, pts)])
            hi = np.array([d["ci"][f"{j}_{f}_{c}"][1] if d["ci"][f"{j}_{f}_{c}"][1] is not None else p for (f, c), p in zip(cats, pts)])
            ax.bar(x + (k - .5) * w, pts, w, color=COL[j], label=NAME[j])
            ax.errorbar(x + (k - .5) * w, pts, yerr=[np.maximum(pts - lo, 0), np.maximum(hi - pts, 0)], fmt="none", ecolor="#222", capsize=2.5, lw=1)
        n_u = ext[S]["groups"]["all_unsupported"]["n"]; n_all = ext[S]["n_claims"]
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(f"Set {S} ({n_u} unsupported of {n_all} claims)", fontsize=9); clean(ax)
    axs[0].set_ylabel("Disagreement among valid pairs"); axs[0].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=300); plt.close(fig)


def errortype(ext, path):
    g = ext["B"]["groups"]
    order = [("edit:addition", "Addition\n(n=%d)"), ("edit:strengthening", "Strengthening\n(n=%d)"), ("edit:contradiction", "Contradiction\n(n=%d)")]
    fig, ax = plt.subplots(figsize=(5.2, 3.5)); x = np.arange(len(order)); w = 0.36
    for k, j in enumerate(J):
        pts = np.array([g[o][j]["sensitivity"] for o, _ in order]); lo = np.array([g[o]["ci"][f"{j}_sens"][0] for o, _ in order])
        hi = np.array([g[o]["ci"][f"{j}_sens"][1] for o, _ in order])
        ax.bar(x + (k - .5) * w, pts, w, color=COL[j], label=NAME[j])
        ax.errorbar(x + (k - .5) * w, pts, yerr=[pts - lo, hi - pts], fmt="none", ecolor="#222", capsize=3, lw=1)
    ax.set_xticks(x); ax.set_xticklabels([l % g[o]["n"] for o, l in order], fontsize=8); ax.set_ylim(0, 1.05)
    ax.set_ylabel("Sensitivity (reference condition)"); ax.legend(frameon=False, fontsize=8, loc="upper left"); clean(ax)
    fig.tight_layout(); fig.savefig(path, dpi=300); plt.close(fig)


if __name__ == "__main__":
    ext = json.load(open(sys.argv[2])); out = sys.argv[3]
    stability(ext, f"{out}/fig_stability_class.png"); errortype(ext, f"{out}/fig_errortype.png")
    print("wrote figures to", out)
