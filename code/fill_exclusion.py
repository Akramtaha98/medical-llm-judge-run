#!/usr/bin/env python3
"""Insert the exclusion sensitivity analysis (data/results_exclusion.json) into manuscript.tex and the abstract.
Run from writing/3_source after code/analysis_exclusion.py. Idempotent: refuses to run twice."""
import json, re
R = json.load(open('../../data/results_exclusion.json'))
t = open('manuscript.tex', encoding='utf-8').read()
assert 'subsec:exclusion' not in t, 'already inserted'
J = {'llama3_8b': 'Llama~3~8B', 'qwen25_7b': 'Qwen2.5~7B'}
f = lambda x: f'{x:.3f}'
def ci(c): return f'{c[0]:.3f}--{c[1]:.3f}'
def line(j):
    r = R[j]['setA_restored197']; e = R[j]['excluded17']
    return (f"{J[j]} flagged {r['tp']} of {r['n_pos']} unsupported claims (sensitivity {f(r['sens'])}, exact 95\\% interval {ci(r['sens_ci'])}) "
            f"and {r['fp']} of {r['n_neg']} supported claims (specificity {f(r['spec'])}); of the 17 restored claims alone, it flagged {e['tp']} of {e['n_pos']} unsupported and {e['fp']} of {e['n_neg']} supported claims")
aa = {j: R[j]['setA_restored197']['always_approved_unsupported'] for j in J}
res = (r"\subsection{Sensitivity analysis: restoring the excluded claims}\label{subsec:exclusion}" "\n\n"
       "Seventeen refusal-type Set A claims, five of them labelled unsupported, had been excluded at the gold stage (Protocol Amendment~4). Both judges were run on these claims after the primary analysis was complete, with the same prompts, seeds, parser and settings (306 sampled and 102 greedy calls, none invalid). With the claims restored, Set A has 197 claims, of which 10 are unsupported. Under the reference condition, "
       + line('llama3_8b') + ". " + line('qwen25_7b') + ". "
       f"Across all nine sampled conditions, {aa['llama3_8b']} of the 10 unsupported claims were approved every time by Llama and {aa['qwen25_7b']} of 10 by Qwen. "
       f"Of the 12 supported restored claims, Llama flagged {R['llama3_8b']['excluded17']['fp']} and Qwen {R['qwen25_7b']['excluded17']['fp']} under the reference condition, so the higher Llama sensitivity on the restored set is accompanied by a high false-positive rate on claims that state the passage does not answer; it should not be read as selective detection of unsupported content. "
       f"Under greedy decoding, the number of the 10 unsupported claims flagged under P1, P2 and P3 was {', '.join(str(R['llama3_8b']['greedy_restored197_per_prompt'][p]['tp']) for p in ['P1','P2','P3'])} for Llama and {', '.join(str(R['qwen25_7b']['greedy_restored197_per_prompt'][p]['tp']) for p in ['P1','P2','P3'])} for Qwen. "
       "With only 10 positive claims drawn from the same questions, these intervals are wide and ignore clustering, so Set A remains descriptive and the conclusions drawn from Set B are unchanged.\n\n")
assert R['llama3_8b']['invalid_on_excluded'] == 0 and R['qwen25_7b']['invalid_on_excluded'] == 0, 'invalid outputs on excluded claims'
anchor = '\\subsection{Failure patterns}'; assert anchor in t
t = t.replace(anchor, res + anchor, 1)
meth = ("\n\n\\paragraph{Sensitivity analysis for the excluded claims.} Because excluding the 17 refusal-type claims was a post-labelling decision, both judges were also run on those claims after the primary analysis was complete, with identical prompts, seeds, parser and settings (306 sampled and 102 greedy calls), and the Set A estimates were recomputed with the claims restored (197 claims, 10 unsupported). This analysis was added after the primary analysis and is descriptive (code/analysis\\_exclusion.py).")
key = "is reported both as a finding and as a limitation of sample size."
assert key in t; t = t.replace(key, key + meth, 1)
disc_key = 'this descriptive result is inconclusive and neither supports nor rules out adequate detection in natural answers.'
assert disc_key in t
t = t.replace(disc_key, disc_key + f" Restoring the 17 excluded refusal-type claims raised observed Set A sensitivity to {R['llama3_8b']['setA_restored197']['tp']}/10 (Llama) and {R['qwen25_7b']['setA_restored197']['tp']}/10 (Qwen), but Llama also flagged {R['llama3_8b']['excluded17']['fp']} of the 12 supported refusal-type claims, so this sensitivity analysis does not change the conclusion.", 1)
open('manuscript.tex', 'w', encoding='utf-8').write(t)
r1, r2 = R['llama3_8b']['setA_restored197'], R['qwen25_7b']['setA_restored197']
sent = f"Restoring 17 excluded refusal-type claims gave Set A sensitivity {r1['tp']}/10 (Llama) and {r2['tp']}/10 (Qwen), but Llama flagged {R['llama3_8b']['excluded17']['fp']}/12 supported refusals."
open('excl_abstract.txt', 'w').write(sent)
print(sent); print(res[:1200])
