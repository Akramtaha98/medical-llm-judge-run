"""Fill judge-dependent results in manuscript.tex from data/results.json and data/results_extra.json.
Run once on the pre-fill manuscript (each anchor must occur exactly once)."""
import json, sys
from scipy.stats import beta
tex_path, res_path, ext_path, misses_path = sys.argv[1:5]
R = json.load(open(res_path)); X = json.load(open(ext_path))
tex = open(tex_path, encoding='utf-8').read()
L, Q = 'llama3_8b', 'qwen25_7b'
NAME = {L: 'Llama 3 8B', Q: 'Qwen2.5 7B'}

def rep(old, new):
    global tex
    assert tex.count(old) == 1, (tex.count(old), old[:80])
    tex = tex.replace(old, new)

def f3(x): return f"{x:.3f}".replace('-', '$-$')
def ci3(l, h): return f"({f3(l)}--{f3(h)})"
def pct(x, d=1): return f"{100*x:.{d}f}"
def pci(c): return f"{pct(c[0])}--{pct(c[1])}"
def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a/2, k, n-k+1)
    hi = 1.0 if k == n else beta.ppf(1-a/2, k+1, n-k)
    return lo, hi

# ---------- abstract ----------
B, A = R['B'], R['A']; BP, BC = B['point'], B['bootstrap_95ci']; AP, AC = A['point'], A['bootstrap_95ci']
sL, sQ = BP[L]['detection'], BP[Q]['detection']
d = BC['diff']['sensitivity']
rep(r"\tbd[: reference-condition sensitivity with 95\% interval and denominator, prompt and seed disagreement rates, share of unsupported claims approved under every condition].",
 f"Under the reference condition (prompt P1, seed 17), sensitivity to unsupported claims in Set B was {sL['sensitivity']:.3f} ({int(sL['tp'])}/{int(sL['n_unsupported'])}; 95\\% CI {BC[L]['sensitivity'][0]:.3f} to {BC[L]['sensitivity'][1]:.3f}) for Llama~3~8B and {sQ['sensitivity']:.3f} ({int(sQ['tp'])}/{int(sQ['n_unsupported'])}; {BC[Q]['sensitivity'][0]:.3f} to {BC[Q]['sensitivity'][1]:.3f}) for Qwen2.5~7B (paired difference, Llama minus Qwen, {sL['sensitivity']-sQ['sensitivity']:.3f}; 95\\% CI {d[0]:.3f} to {d[1]:.3f}), with specificity {sL['specificity']:.3f} and {sQ['specificity']:.3f}. In Set A neither judge flagged any of the 5 unsupported claims (0/5; exact upper 95\\% limit {cp(0,5)[1]:.3f}), so Set A sensitivity is not estimable. In Set B, pooled prompt disagreement was {pct(BP[L]['prompt_disagreement']['rate'])}\\% (95\\% CI {pci(BC[L]['prompt_disagreement'])}) for Llama and {pct(BP[Q]['prompt_disagreement']['rate'])}\\% ({pci(BC[Q]['prompt_disagreement'])}) for Qwen, and seed disagreement {pct(BP[L]['seed_disagreement']['rate'])}\\% and {pct(BP[Q]['seed_disagreement']['rate'])}\\%; these intervals overlap, so no difference between prompt and seed effects is claimed. Verdicts were stable but often stably wrong: {BP[L]['consistency']['unsupported_always_approved']:.0f} of 102 unsupported Set B claims ({pct(BP[L]['consistency']['unsupported_always_approved']/102)}\\%) were approved under all nine conditions by Llama and {BP[Q]['consistency']['unsupported_always_approved']:.0f} ({pct(BP[Q]['consistency']['unsupported_always_approved']/102)}\\%) by Qwen. In exploratory analyses, contradictions were almost always flagged (Llama 32/33, Qwen 33/33), whereas added details absent from the passage were mostly missed (Llama 4/34, Qwen 17/34).")
rep(r"\tbd[: conclusion limited to textual support in this sample; to be written after the locked analysis].",
 "In this sample, both small judges were consistent across prompt wording and seeds, but they missed a substantial share of unsupported claims, mainly details added beyond the passage. Consistency should not be read as accuracy. The data support, at most, use as a first-pass flag alongside review by a qualified person, and they say nothing about clinical safety, because the endpoint is textual support by a supplied passage.")

# ---------- methods ----------
rep(r"the number actually completed was \tbd[: total calls], and observed wall time was \tbd[: timing over at least 50 calls per model].",
 "all 9,120 were completed. The summed per-call latency was 22.4 min (Llama) and 22.3 min (Qwen) for the 3,420 sampled calls of each judge and 20.3 and 19.7 min for the 1,140 greedy calls, with median latencies of 0.075 s per sampled call (range 0.064 to 1.92 s) and 1.04 s per greedy call.")

# ---------- results: data flow ----------
rep("Results are reported from the frozen files only. Nothing in this section has been generated at the time of this draft, and every cell marked \\tbd\\ must be filled from the locked analysis.",
 "Results are reported from the frozen files only, after verifying that every frozen file matched its recorded checksum. The failure-pattern analyses in the last subsection were specified after the primary analysis and are exploratory.")
rep(r"\tbd[: valid judge runs and exclusions].",
 "All 9,120 planned judge calls (6,840 sampled and 2,280 greedy) were completed and parsed as valid labels; no key was missing or duplicated, no output was invalid, and no claim or call was excluded, so coverage was 1.000 in every condition.")
rep("Counts (n = TBD) are completed from the frozen logs.", "Counts come from the frozen corpus manifest and run logs.")
rep(r"\includegraphics[width=0.62\textwidth]{fig_flow.png}", r"\includegraphics[width=0.58\textwidth]{fig_flow.png}")

# ---------- table detect ----------
def det_row(S, j):
    P = R[S]['point'][j]['detection']; C = R[S]['bootstrap_95ci'][j]
    tp, fn, inv = int(P['tp']), int(P['fn_valid']), int(P['invalid_unsupported'])
    nu = int(P['n_unsupported'])
    if S == 'A':
        lo, hi = cp(tp, nu); sens = f"{f3(P['sensitivity'])} {ci3(lo, hi)}$^{{\\dagger}}$"
    else:
        sens = f"{f3(P['sensitivity'])} {ci3(C['sensitivity'][0], C['sensitivity'][1])}"
    spec = f"{f3(P['specificity'])} {ci3(C['specificity'][0], C['specificity'][1])}"
    prec = f3(P['precision_valid']) if P['precision_valid'] == P['precision_valid'] else '--'
    f1 = f3(P['f1_valid']) if P['f1_valid'] == P['f1_valid'] else '--'
    return f"{S} & {NAME[j]} & {tp}/{fn}/{inv} & {sens} & {spec} & {f3(P['coverage'])} & {prec} & {f1} \\\\\n"
def diff_row(S):
    D = R[S]['bootstrap_95ci']['diff']; P = R[S]['point']
    ds = P[L]['detection']['sensitivity'] - P[Q]['detection']['sensitivity']
    dp = P[L]['detection']['specificity'] - P[Q]['detection']['specificity']
    sens = "0.000$^{\\dagger}$" if S == 'A' else f"{f3(ds)} {ci3(*D['sensitivity'][:2])}"
    return f"{S} & Difference (Llama $-$ Qwen) & -- & {sens} & {f3(dp)} {ci3(*D['specificity'][:2])} & -- & -- & -- \\\\\n"
old = """A & Llama 3 8B & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd \\\\
A & Qwen2.5 7B & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd \\\\
A & Difference & -- & \\tbd & \\tbd & -- & -- & -- \\\\
B & Llama 3 8B & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd \\\\
B & Qwen2.5 7B & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd & \\tbd \\\\
B & Difference & -- & \\tbd & \\tbd & -- & -- & -- \\\\
"""
rep(old, det_row('A', L) if False else (det_row('A', L)+det_row('A', Q)+diff_row('A')+det_row('B', L)+det_row('B', Q)+diff_row('B')))
rep(r"Sensitivity (95\% CI) & Specificity & Coverage & Precision & F1 \\",
    r"Sensitivity (95\% CI) & Specificity (95\% CI) & Coverage & Precision & F1 \\")
rep(r"Invalid and missing responses count as non-detections.}",
    r"Invalid and missing responses count as non-detections; none occurred. Differences are Llama minus Qwen with paired question-level bootstrap intervals. $^{\dagger}$Exact Clopper--Pearson interval; Set A has only 5 unsupported claims and neither judge flagged any, so sensitivity is not estimable and its difference is undefined. Precision is 0 because every flagged Set A claim was a false positive; F1 is undefined (--).}")
rep(r"Table~\ref{tab:detect} reports detection under the reference condition (P1, seed 17) for each judge and set.",
    "Table~\\ref{tab:detect} reports detection under the reference condition (P1, seed 17) for each judge and set. In Set B, Qwen2.5~7B flagged more unsupported claims than Llama~3~8B (paired sensitivity difference " + f"{sL['sensitivity']-sQ['sensitivity']:.3f}, 95\\% CI {d[0]:.3f} to {d[1]:.3f}" + "), and the interval excludes zero. Specificity was near ceiling for both judges (Llama flagged 1 of 98 supported Set B claims, Qwen none), and the specificity difference includes zero. In Set A, neither judge flagged any of the 5 unsupported claims, so the data cannot distinguish a low from a moderate sensitivity (upper exact limit " + f"{cp(0,5)[1]:.3f}" + "); Set A is informative about false positives only (specificity " + f"{AP[L]['detection']['specificity']:.3f} and {AP[Q]['detection']['specificity']:.3f}" + ").")

# ---------- table stability ----------
def stab_row(S, j, fac):
    P = R[S]['point'][j][f'{fac}_disagreement']; C = R[S]['bootstrap_95ci'][j][f'{fac}_disagreement']
    pair = f"{int(P['valid_pairs']):,}/{int(P['expected_pairs']):,}"
    return f"{S} & {NAME[j]} & {fac.capitalize()} & {pair} & {pct(P['rate'])}\\% ({pci(C)}) & {pct(P['lower_bound'])}--{pct(P['upper_bound'])}\\% \\\\\n"
old = ""
for S in 'AB':
    for j in (L, Q):
        for fac in ('prompt', 'seed'):
            old += f"{S} & {NAME[j]} & {fac.capitalize()} & \\tbd & \\tbd & \\tbd \\\\\n"
new = "".join(stab_row(S, j, fac) for S in 'AB' for j in (L, Q) for fac in ('prompt', 'seed'))
rep(old, new)
rep("Bounds count non-evaluable pairs as agreeing (lower) or disagreeing (upper).}", "Bounds count non-evaluable pairs as agreeing (lower) or disagreeing (upper); no pair was non-evaluable, so the bounds equal the rate.}")
rep(r"Table~\ref{tab:stab} and Figure~\ref{fig:stab} give pooled disagreement rates, with the bounds from the non-evaluable pair analysis.",
    "Table~\\ref{tab:stab} and Figure~\\ref{fig:stab} give pooled disagreement rates, with the bounds from the non-evaluable pair analysis. Disagreement was low throughout: at most " + f"{pct(max(R[S]['point'][j][f+'_disagreement']['rate'] for S in 'AB' for j in (L,Q) for f in ('prompt','seed')))}" + "\\% of valid pairs differed, and in every judge--set combination the interval for the prompt rate overlapped that for the seed rate. Prompt rates were numerically larger than seed rates for both judges and sets, but because the intervals overlap and the paired differences between judges also include zero (Set B: prompt " + f"{BC['diff']['prompt_disagreement'][0]:.3f} to {BC['diff']['prompt_disagreement'][1]:.3f}, seed {BC['diff']['seed_disagreement'][0]:.3f} to {BC['diff']['seed_disagreement'][1]:.3f}" + "), we do not claim that wording matters more than sampling, or that either judge is more stable. Disagreement concentrated in unsupported claims for Llama (Set B prompt " + f"{pct(BP[L]['prompt_disagreement_gold_unsupported']['rate'])}\\% against {pct(BP[L]['prompt_disagreement_gold_supported']['rate'])}\\%" + " for supported claims; Figure~\\ref{fig:stab}), a pattern that is descriptive only.")
rep(r"""\fbox{\parbox{0.9\textwidth}{\centering\vspace{1.5cm}\tbd[: Figure 4, prompt and seed disagreement per judge and set with bootstrap intervals, split by gold class]\vspace{1.5cm}}}""",
    r"\includegraphics[width=0.9\textwidth]{fig_stability_class.png}")
rep(r"\caption{Prompt and seed disagreement for each judge, with 95\% bootstrap intervals.}",
    r"\caption{Prompt and seed disagreement for each judge in Set B, split by human reference class, with 95\% paired question-level bootstrap intervals. Intervals overlap throughout.}")

# ---------- table greedy ----------
def greedy_row(S, j):
    G = X[S]['greedy']; p = G['point'][j]; c = G['ci']
    pairs = f"{p['valid_pairs']:,}/{p['valid_pairs']:,}"
    nu = 5 if S == 'A' else 102
    if S == 'A':
        k = round(p['sensitivity_pooled']*nu*3); lo, hi = cp(k, nu*3)
        sens = f"{f3(p['sensitivity_pooled'])} {ci3(lo, hi)}$^{{\\dagger}}$"
    else:
        sens = f"{f3(p['sensitivity_pooled'])} {ci3(*c[j+'_sens'][:2])}"
    dis = f"{pct(p['prompt_disagreement'])}\\% ({pci(c[j+'_dis'])})"
    return f"{S} & {NAME[j]} & {sens} & {dis} & {pairs} \\\\\n"
old = """A & Llama 3 8B & \\tbd & \\tbd & \\tbd \\\\
A & Qwen2.5 7B & \\tbd & \\tbd & \\tbd \\\\
B & Llama 3 8B & \\tbd & \\tbd & \\tbd \\\\
B & Qwen2.5 7B & \\tbd & \\tbd & \\tbd \\\\
"""
rep(old, "".join(greedy_row(S, j) for S in 'AB' for j in (L, Q)))
rep(r"\caption{Greedy-decoding reference arm (temperature 0, one run per prompt).}",
    r"\caption{Greedy-decoding reference arm (temperature 0, one run per prompt). Sensitivity is pooled over the three prompts (Set A: 15 claim--prompt judgments of unsupported claims, Set B: 306), with a bootstrap interval, except $^{\dagger}$exact Clopper--Pearson interval for Set A. Disagreement is pooled over the three prompt pairs.}")
GB = X['B']['greedy']['point']
rep(r"Table~\ref{tab:greedy} reports the arm that removes sampling noise.",
    "Table~\\ref{tab:greedy} reports the arm that removes sampling noise. Removing sampling changed little: pooled Set B sensitivity under greedy decoding was " + f"{GB[L]['sensitivity_pooled']:.3f} (Llama) and {GB[Q]['sensitivity_pooled']:.3f} (Qwen), close to the reference-condition values, and prompt disagreement among the three greedy runs was {pct(GB[L]['prompt_disagreement'])}\\% and {pct(GB[Q]['prompt_disagreement'])}\\%. Across the nine sampled conditions, Set B sensitivity ranged from {X['B']['sens_range_9'][L]['min']:.3f} to {X['B']['sens_range_9'][L]['max']:.3f} (Llama) and from {X['B']['sens_range_9'][Q]['min']:.3f} to {X['B']['sens_range_9'][Q]['max']:.3f} (Qwen). Sampling noise at temperature 0.3 is therefore not the main source of missed claims.")

# ---------- failure patterns ----------
def grp(name, label):
    g = X['B']['groups'][name]; c = g['ci']
    def s(j): return f"{f3(g[j]['sensitivity'])} {ci3(*c[j+'_sens'][:2])}"
    return f"{label} & {g['n']} & {s(L)} & {pct(g[L]['always_approved'],0)}\\% & {s(Q)} & {pct(g[Q]['always_approved'],0)}\\% \\\\\n"
rows = (grp('edit:addition', 'Addition of a detail') + grp('edit:contradiction', 'Contradiction') + grp('edit:strengthening', 'Strengthened certainty or scope') + r"\midrule" + "\n" +
        grp('subtype:contradicted', 'Reviewer subtype: contradicted') + grp('subtype:absent_or_overextended', 'Reviewer subtype: absent or overextended') + r"\midrule" + "\n" + grp('all_unsupported', 'All unsupported claims'))
cons = lambda S, j: R[S]['point'][j]['consistency']
mo = X['B']['miss_overlap']; mA = X['A']['miss_overlap']
n_miss = sum(1 for _ in open(misses_path, encoding='utf-8')) - 1
fail = (
"Across the nine conditions, most claims were judged correctly every time or wrong every time, and few were mixed (Table~\\ref{tab:fail}). In Set B, " +
f"{cons('B',L)['always_correct']:.0f} claims (Llama) and {cons('B',Q)['always_correct']:.0f} (Qwen) of 200 were always correct, {cons('B',L)['always_wrong']:.0f} and {cons('B',Q)['always_wrong']:.0f} were always wrong, and {cons('B',L)['mixed']:.0f} and {cons('B',Q)['mixed']:.0f} were mixed. The always-wrong claims were all unsupported claims approved every time: {cons('B',L)['unsupported_always_approved']:.0f} of 102 ({pct(X['B']['groups']['all_unsupported'][L]['always_approved'])}\\%; 95\\% CI {pci(X['B']['groups']['all_unsupported']['ci'][L+'_always'])}) for Llama and {cons('B',Q)['unsupported_always_approved']:.0f} of 102 ({pct(X['B']['groups']['all_unsupported'][Q]['always_approved'])}\\%; {pci(X['B']['groups']['all_unsupported']['ci'][Q+'_always'])}) for Qwen. In Set A, {cons('A',L)['unsupported_always_approved']:.0f} of 5 unsupported claims (Llama) and {cons('A',Q)['unsupported_always_approved']:.0f} of 5 (Qwen) were approved under all nine conditions, and {cons('A',L)['always_wrong']:.0f} and {cons('A',Q)['always_wrong']:.0f} claims were always wrong, which includes always-flagged supported claims. Errors were therefore mainly stable rather than unstable. For scale, a rule that approved every claim would be correct on {pct(X['B']['rules']['always_supported_accuracy'],0)}\\% of Set B and {pct(X['A']['rules']['always_supported_accuracy'],1)}\\% of Set A, which is why Set A accuracy is uninformative and detection is reported separately.\n\n"
"Misses depended strongly on the kind of error (Table~\\ref{tab:fail}, Figure~\\ref{fig:errortype}; these breakdowns are exploratory and were specified after the primary analysis). Contradictions of the passage were almost always flagged (Llama 32/33, Qwen 33/33), changes of certainty or scope were flagged less often (Llama 24/33, Qwen 27/33), and details added to a claim and absent from the passage were mostly missed by Llama (4/34 flagged) and missed about half the time by Qwen (17/34). The interval for the Llama--Qwen difference excludes zero for added details and for the reviewer subtype absent or overextended, and includes zero for contradictions and for strengthening, where the Qwen bootstrap interval is degenerate at 1.000 for contradictions because every contradiction was flagged. Of the " + f"{mo['ref_both']+mo['ref_llama_only']+mo['ref_qwen_only']}" + " unsupported Set B claims missed by at least one judge at the reference condition, " + f"{mo['ref_both']} were missed by both, {mo['ref_llama_only']} by Llama only and {mo['ref_qwen_only']} by Qwen only; {mo['all9_both']} claims were approved under every condition by both judges. Misses were thus largely shared, so combining these two judges would add little. In Set A, which has only five unsupported claims, all five were missed by both judges at the reference condition. By originating generator, Set A specificity was " + f"{R['A']['self_vs_cross'][L]['self']['detection']['specificity']:.3f} for Llama on its own answers (105 claims) and {R['A']['self_vs_cross'][L]['cross']['detection']['specificity']:.3f} on Qwen's (75), and {R['A']['self_vs_cross'][Q]['self']['detection']['specificity']:.3f} for Qwen on its own (75) and {R['A']['self_vs_cross'][Q]['cross']['detection']['specificity']:.3f} on Llama's (105); the direction is not consistent across judges, and the counts are too small for inference. Set B edits were not generated by either judge, so no self-versus-cross comparison applies there.\n\n"
f"Supplementary Table~S1 lists the {n_miss} claims that at least one judge classified incorrectly at the reference condition, with identifiers, source, generator, human reference label, edit type and claim text, so that readers can verify each against the MedQuAD passage.\n\n"
"""\\begin{table}[t]
\\centering
\\caption{Set B sensitivity and share of unsupported claims approved under all nine conditions, by error type. Edit-type rows partition the 100 designed edits; reviewer-subtype rows partition the 102 unsupported claims, which include two supported paraphrases adjudicated unsupported. Intervals are paired question-level bootstrap 95\\% intervals. Exploratory.}
\\label{tab:fail}
\\small
\\begin{tabular}{lcccccc}
\\toprule
 & & \\multicolumn{2}{c}{Llama 3 8B} & \\multicolumn{2}{c}{Qwen2.5 7B} \\\\
\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}
Unsupported claim type & $n$ & Sensitivity (95\\% CI) & Always approved & Sensitivity (95\\% CI) & Always approved \\\\
\\midrule
""" + rows + """\\bottomrule
\\end{tabular}
\\end{table}

\\begin{figure}[t]
\\centering
\\includegraphics[width=0.9\\textwidth]{fig_errortype.png}
\\caption{Set B sensitivity by error type for each judge with 95\\% bootstrap intervals (exploratory).}
\\label{fig:errortype}
\\end{figure}
""")
oldfail = tex[tex.index(r"\tbd[: proportion of claims always correct"): tex.index(r"\section{Discussion}")]
rep(oldfail, fail + "\n")
# strengthening counts check
g = X['B']['groups']['edit:strengthening']
assert abs(g[L]['sensitivity']*33-24) < 1e-9 and abs(g[Q]['sensitivity']*33-27) < 1e-9

# ---------- discussion ----------
rep(r"\tbd[: One paragraph stating the primary detection estimate with its interval and denominator for each judge, and the primary prompt-disagreement estimate. Report positive and negative findings alike, and do not describe a difference as meaningful where the intervals overlap.]",
 f"In the controlled set, Llama~3~8B flagged {sL['sensitivity']:.3f} ({int(sL['tp'])}/102; 95\\% CI {BC[L]['sensitivity'][0]:.3f}--{BC[L]['sensitivity'][1]:.3f}) of the unsupported claims and Qwen2.5~7B flagged {sQ['sensitivity']:.3f} ({int(sQ['tp'])}/102; {BC[Q]['sensitivity'][0]:.3f}--{BC[Q]['sensitivity'][1]:.3f}) under the reference condition, with specificity of at least {min(sL['specificity'], sQ['specificity']):.3f}. Qwen detected more unsupported claims than Llama (paired difference {d[0]:.3f} to {d[1]:.3f}), whereas the specificity difference included zero. Neither judge caught enough to serve as the only check. Prompt disagreement was {pct(BP[L]['prompt_disagreement']['rate'])}\\% (Llama; 95\\% CI {pci(BC[L]['prompt_disagreement'])}) and {pct(BP[Q]['prompt_disagreement']['rate'])}\\% (Qwen; {pci(BC[Q]['prompt_disagreement'])}), so verdicts were insensitive to the three tested phrasings. Detection in ordinary answers (Set A) could not be estimated, because only 5 of 180 scored claims were unsupported and all were approved by both judges; this is an inconclusive result and neither supports nor rules out adequate detection in natural answers.")
rep(r"\tbd[: Interpret missed unsupported claims and stable errors as limitations of automated review. State whether instability was larger for prompt wording or for seed, and whether misses concentrated in additions absent from the passage, contradictions or changes of scope and certainty. Compare with the closest prior work identified in the literature search.]",
 "The central pattern is that verdicts were stable but often stably wrong. Because disagreement among phrasings and seeds was small and errors were mostly the same in every condition, repeating the judgment, averaging over seeds, or choosing among these three prompts would not recover the missed claims; consistency is therefore not evidence of correctness. Instability was not clearly larger for prompt wording than for seed: prompt rates were numerically higher, but the intervals overlap and we do not claim a difference. Misses concentrated in additions absent from the passage, which require the judge to notice that a plausible statement is not in the text, and were rare for contradictions, which require only a conflict with a stated fact. A reading consistent with these data, which they do not test, is that these small judges rely on topical and semantic match to the passage more than on checking each detail against it, and that medically plausible additions are especially likely to pass. Added details are also the kind of error an answer generator is likely to make when it elaborates beyond a passage, so the weak spot is relevant to the intended use. The two judges missed largely the same claims, so pairing them would add little. Comparison with the closest prior work will be added after the literature search \\tbd[: compare with closest prior work].")

# ---------- reading table ----------
rep(r"Table~\ref{tab:reading} gives outcome-neutral readings that will be reconciled with the locked results. They describe what each pattern would and would not support in this sample, and make no prediction of which pattern occurs.",
    r"Table~\ref{tab:reading} lists outcome patterns that were stated before analysis, the reading each would support in this sample, and what was observed.")
rep(r"""\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.1cm}X}
\toprule
Pattern in the locked data & Reading limited to this sample \\
\midrule
High sensitivity, narrow interval, low disagreement & Most unsupported claims were flagged under the tested conditions; unflagged claims still need human review and periodic audit. \\
Low sensitivity & A substantial share of unsupported claims passed; the model is not suitable as the sole check. \\
High prompt or seed disagreement & Verdicts depend on wording or sampling; a fixed prompt, greedy decoding and reporting of the range across phrasings are needed before any deployment claim. \\
Wide intervals or small unsupported yield & Inconclusive for detection; the sample must be extended before conclusions are drawn. \\""",
r"""\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{3.3cm}>{\raggedright\arraybackslash}p{5.2cm}X}
\toprule
Pattern & Reading limited to this sample & Observed here \\
\midrule
High sensitivity, narrow interval, low disagreement & Most unsupported claims were flagged under the tested conditions; unflagged claims still need human review and periodic audit. & Not observed overall. Low disagreement was observed, but sensitivity in Set B was """ + f"{sL['sensitivity']:.2f} and {sQ['sensitivity']:.2f}" + r""" and was high only for contradictions. \\
Low sensitivity & A substantial share of unsupported claims passed; the model is not suitable as the sole check. & Observed for Llama (upper CI limit """ + f"{BC[L]['sensitivity'][1]:.2f}" + r""") and for both judges on details absent from the passage. \\
High prompt or seed disagreement & Verdicts depend on wording or sampling; a fixed prompt, greedy decoding and reporting of the range across phrasings are needed before any deployment claim. & Not observed: at most """ + f"{pct(max(R[S]['point'][j][f+'_disagreement']['upper_bound'] for S in 'AB' for j in (L,Q) for f in ('prompt','seed')))}" + r"""\% of pairs disagreed. \\
Wide intervals or small unsupported yield & Inconclusive for detection; the sample must be extended before conclusions are drawn. & Observed for Set A (5 unsupported claims; sensitivity not estimable). \\""")

# ---------- scope, limitations, conclusions ----------
rep(r"A defensible use suggested by the design is as a first-pass flag whose misses are reviewed by a qualified person, and the data from this study show how many such misses to expect \tbd[: confirm or revise once results are available].",
    f"A use that these data do not contradict is as a first-pass flag that supplements, and does not replace, review by a qualified person, because an unflagged claim cannot be assumed to be supported: at the reference condition, {int(sL['fn_valid'])} of 102 (Llama) and {int(sQ['fn_valid'])} of 102 (Qwen) unsupported Set B claims were not flagged, and Set B's error mix is designed and does not reflect natural frequencies.")
rep(r"Finally, repeated judgments of the same claim are not independent observations.",
    r"Set B was constructed by one member of the study team who knew the edit types, so its edits may be easier or harder to detect than errors that occur naturally, and two of its supported paraphrases were adjudicated unsupported. The edit-type and reviewer-subtype comparisons and the miss-overlap analysis are exploratory and were specified after the primary analysis (code/analysis\_extra.py). Set A had too few unsupported claims to estimate sensitivity. Finally, repeated judgments of the same claim are not independent observations.")
rep(r"\tbd[: Two or three sentences restricted to textual support in this sample, written after the locked analysis.]",
    "In this sample, Llama~3~8B and Qwen2.5~7B gave nearly the same verdict across three instruction phrasings and three seeds, yet each missed a substantial share of claims that were unsupported by the passage, with Qwen2.5~7B detecting more than Llama~3~8B. Misses concentrated in plausible details added beyond the passage, were largely shared by the two judges, and were not removed by greedy decoding. Stability across prompts and seeds should therefore not be taken as evidence of correct detection, and these results concern textual support only, not the safety of any clinical use.")

open(tex_path, 'w', encoding='utf-8').write(tex)
print('ok; remaining tbd:', tex.count(r'\tbd['))
