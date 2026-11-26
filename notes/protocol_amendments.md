# Protocol amendment log (pre-freeze)

Record every change to prompts, generation settings, selection rules or parser made before test inference.
Do not edit past entries. Add a new entry for each change.

| # | Date | Change | Reason | Judge outputs seen before change? |
|---|------|--------|--------|-----------------------------------|
| 1 | 2026-11-24 | Set A generation: max new tokens 160 -> 256; all 112 answers regenerated under the same settings | First run: 3 of 112 answers (all Llama 3) did not end in terminal punctuation, at least one cut mid-sentence; longest answer 130 words. Format/length-limit problem, not an answer-quality judgment | No |
| 2 | 2026-11-25 | Judge prompts aligned with Methods: fixed system message; user message = one varying instruction sentence (P1-P3 as in Methods) followed by delimited [PASSAGE], [QUESTION], [CLAIM] fields; question now passed to the judge | Earlier prompts.py omitted the question and used different wording than the manuscript; code brought into line with the written protocol before any judge run on study data | No |
| 3 | 2026-11-25 | Judge calls (both judges, both arms) now use stop sequence "\n" (generation ends at the first newline). Strict whole-output parser unchanged; output cap unchanged at 8 tokens | Format failure, not a judgment about claim correctness: in the dev-claim pilot (20 draft claims from the 12 dev questions, prompts of amendment #2) Qwen2.5 7B returned a bare label followed by an explanation and was marked invalid in 54/180 sampled calls and 19/60 greedy calls; Llama 3 8B had 0/180 sampled and 0/60 greedy invalid. All invalid Qwen outputs began with SUPPORTED | No (dev claims only; no test claim run; pilot claims unlabelled) |
| 4 | 2026-11-26 | Set A minimum-yield rule replaced (see entry below). 17 refusal or "does not answer" claims excluded from claim scoring at the gold stage (list: data/claims/refusal_excluded.csv). code/label_tools.py gold gained --exclude; no prompt, setting, parser or selection rule changed | Original rule: fewer than 30 adjudicated unsupported Set A claims -> draw from data/corpus/reserve.csv in order. Observed 10 (5 after excluding refusals) of 197 (180) Set A claims; the 182 reserve questions would add only about 10 to 18 | No |
| 5 | 2026-11-26 | Greedy reference arm added: temperature 0, seed 17, prompts P1-P3, both judges, all 380 gold claims (2,280 calls); secondary and descriptive | Estimates prompt disagreement without sampling noise; deterministic and replay-verified on the dev pilot | No |

## Amendment 4 (2026-11-26): Set A minimum-yield rule and refusal-type claims

Written after reference labelling and adjudication of the 397 test claims and before any judge output was run, opened or analysed. Judge outputs seen: none.

**Original rule.** If fewer than 30 adjudicated unsupported Set A claims were obtained, further questions would be drawn from data/corpus/reserve.csv in order and processed identically.

**Observation.** Adjudicated gold labels (R1, R2, R3) gave 10 unsupported of 197 Set A claims (5.1 percent, exact 95 percent CI 2.5 to 9.1). Five of those were refusal-type claims ("the passage does not answer ...").

**Refusal-type claims.** The Methods state that courtesies and refusals are excluded from claim scoring. Seventeen Set A claims that assert only that the passage does not answer or mention something were excluded from the gold standard and are reported at answer level (data/claims/refusal_excluded.csv, data/labels/gold_excluded.csv). Three claims that mention the passage but describe its content were kept (A-NIDDK-0000128-4-01, A-NIDDK-0000158-13-03, A-NIDDK-0000162-3-02). The classification was made by the study lead from claim wording, after labelling, with the reviewers' labels visible and without any judge output. This makes it a post-labelling decision and it is reported as such; a sensitivity analysis that keeps these claims is possible because their labels were collected and are retained.

**After exclusion.** Set A has 180 scored claims, 175 supported and 5 unsupported (2.8 percent, exact Clopper-Pearson 95 percent CI 0.9 to 6.4). The 5 unsupported claims are all absent_or_overextended. No unassessable claims remain.

**New rule.** The reserve draw is not performed. Drawing all 182 reserve questions would be expected to add about 10 unsupported Set A claims (about 15 in total), still below 30, at the cost of about four further annotation rounds. Instead:
1. Set B, whose error mix is balanced by design (98 supported claims and 102 unsupported claims: 34 addition, 33 contradiction, 33 strengthening, plus 2 paraphrases adjudicated unsupported), is the primary inferential set for detection and decision stability by error type.
2. Set A is reported descriptively: the natural unsupported rate with exact confidence intervals, judge decisions on the 180 claims, and judge precision at this low prevalence. Claim-level detection metrics for Set A (recall, F1) are exploratory, carry wide intervals with only 5 positives, and subgroup analyses of Set A are not performed.
3. The low natural rate of unsupported content in the two generators' answers is reported as a finding and as a sample-size limitation.

**Not changed.** Prompts, seeds, temperatures, judge models, parser, selection of the 112 questions, claim segmentation and the Set B construction.

**Still open.** None; the greedy arm was decided in Amendment 5.

## Amendment 5 (2026-11-26): Greedy reference arm

Decided and logged before any judge was run on test claims. Judge outputs seen on test claims: none. The only judge outputs seen are from the development pilot of 20 unlabelled draft claims (Amendment 3).

The greedy arm (temperature 0, seed 17, prompts P1 to P3, both judges) is run on all 380 gold claims (180 Set A, 200 Set B), giving 2,280 additional calls. It is a secondary, descriptive arm for prompt disagreement without sampling noise and does not enter the primary endpoints. Settings, prompts, parser and stop sequence are otherwise identical to the sampled arm. The arm had been described in the Methods and design figure since the earlier draft but had not been logged; this entry records it with the real date.
