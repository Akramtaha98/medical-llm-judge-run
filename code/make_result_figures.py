#!/usr/bin/env python3
"""Result figures from analysis.py output (results.json). Run only on the locked study data.
  python make_result_figures.py results.json outdir
Produces fig_detection.png (sensitivity with 95% CI per judge and set) and
fig_stability.png (prompt and seed disagreement with 95% CI per judge and set)."""
import json, sys, os
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OI = ["#0072B2", "#E69F00"]  # colorblind-safe, one colour per judge

def _panel(ax, res, metric_path, ylabel, title):
    sets = sorted(res); judges = sorted(res[sets[0]]["point"]); x = np.arange(len(sets)); w = 0.35
    for k, j in enumerate(judges):
        pts, lo, hi = [], [], []
        for s in sets:
            p = res[s]["point"][j]
            for key in metric_path[0]: p = p[key]
            ci = res[s]["bootstrap_95ci"][j][metric_path[1]]
            pts.append(p); lo.append(ci[0] if ci[0] is not None else p); hi.append(ci[1] if ci[1] is not None else p)
        pts, lo, hi = (np.nan_to_num(np.array(v, dtype=float)) for v in (pts, lo, hi))
        ax.bar(x + (k - .5) * w, pts, w, color=OI[k], label=j)
        ax.errorbar(x + (k - .5) * w, pts, yerr=[pts - lo, hi - pts], fmt="none", ecolor="#222222", capsize=3, lw=1)
    ax.set_xticks(x); ax.set_xticklabels([f"Set {s}" for s in sets]); ax.set_ylim(0, 1)
    ax.set_ylabel(ylabel); ax.set_title(title, fontsize=9)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)

def main(path, outdir):
    res = json.load(open(path)); os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    _panel(ax, res, (("detection", "sensitivity"), "sensitivity"), "Sensitivity (unsupported = positive)", "Reference condition (P1, seed 17)")
    ax.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(f"{outdir}/fig_detection.png", dpi=300); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    _panel(axs[0], res, (("prompt_disagreement", "rate"), "prompt_disagreement"), "Disagreement among valid pairs", "Prompt wording")
    _panel(axs[1], res, (("seed_disagreement", "rate"), "seed_disagreement"), "", "Sampling seed")
    axs[0].legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(f"{outdir}/fig_stability.png", dpi=300); plt.close(fig)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
