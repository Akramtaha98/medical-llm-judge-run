# Annotation log (human reference standard)

Append new entries; do not edit past ones.

## 2026-11-25: Practice round (training only)
- Material: 8 invented items (blood-pressure passage) from practice_form.xlsx. Not study text.
- Decision: **practice labels are not study data.** They are not used in agreement statistics, calibration, gold labels or any analysis. Files kept for the record only.
- Reviewers (codes normalized; credentials as self-entered):
  - R1: Master's in bioscience, 2 years biomedical experience, English good.
  - R2: PhD in nursing, nurse, 6 years, English fluent.
  - R3 (adjudicator): PhD, pharmacist, 15 years, English fluent.
- Outcome against the practice key: R1 8/8, R2 7/8. The one disagreement (P05, "Exercising for 30 minutes a day lowers blood pressure") was adjudicated by R3 as unsupported (absent_or_overextended), matching the key. R2 had labelled it supported.
- Integrity check: no read-only column changed; all evidence spans copied verbatim from the passage.
- Follow-ups:
  1. Hold one short discussion of P05 with R2 (allowed by the guide).
  2. Calibration on development claims, target at least 80% raw agreement; only after segmentation is checked.
  3. Each reviewer confirms in writing whether any AI tool or translator was used (the guide forbids it). Record answers here.
  4. Report R1's qualification as entered in the Methods; check it meets the "suitably qualified" wording or revise the wording.
  5. Reviewer codes on the information sheets were not normalized by the reviewers (R2: "Reviewer 2", R3: "R3 (Adjudicator)"); use R1, R2, R3 in all study files.

## 2026-11-25: Composite question key fix (before any human work)
- Problem: MedQuAD question IDs repeat across collections (`0000095-1` is in both NIDDK and NHLBI). Code that joined on `question_id` alone would have produced duplicate claim IDs, shown one question's passage for the other's claims in labelling forms and judge inputs, and merged two questions in the bootstrap.
- Fix: every join now uses `(source, question_id)`. In all downstream files (claims, worksheets, forms, gold, items) the column `question_id` holds the composite key `SOURCE-qid` (for example `NIDDK-0000095-1`); claim IDs are `A-NIDDK-0000095-1-01` and `B-NIDDK-0000095-1-S/E`. Helper: `code/qkeys.py`. Patched: segment_claims.py, make_setB.py, label_tools.py, build_items.py, analysis.py (guard), run_generate.py (assignment keyed by source and ID; the shuffle input is unchanged, so no recorded generator differs from the corrected assignment).
- `data/corpus/selected.csv` and its hash (c75d52a9...) are unchanged. The hash is computed as in build_corpus.py (text-mode read, UTF-8).
- Test: `python code/test_keys.py` (hash, uniqueness, key consistency, synthetic collision through the labelling export). All checks pass; the old sheets failed it before regeneration.
- Regenerated (both were entirely unfilled, 0 cells): `data/claims/segmentation_review.csv` (226 draft claims, 132 flagged, claim texts identical) and `data/claims/setB_worksheet.csv` (112 rows; edit types and presentation order identical to before).
- Not a protocol amendment: no prompt, setting, selection rule or parser changed, and no judge output has been seen.
- Roles: segmentation check = Akram. Set B edits = one of Fanan or Mohammed (to be confirmed; credit in Methods once confirmed). `label_tools.py export` has not been run.

## 2026-11-25: Role assignment confirmed
- Segmentation check (segmentation_review.csv): Akram.
- Set B edits (setB_worksheet.csv): Fanan. Fanan takes no part in reference labelling or adjudication and sees no judge output. The edits are written by hand without a language model (state this in the CRediT line: Set B construction, Fanan).
- Methods sentence updated in manuscript.tex (anonymized: "one member of the study team").

## 2026-11-25 Author task packages
- Built writing/5_author_tasks/: Akram (segmentation_check.xlsx + guide), Fanan (setB_edits.xlsx + guide); converter code/task_sheets.py (round trip tested; read-only columns enforced).
- Not a protocol amendment. Open for confirmation: list-splitting rule in Akram's guide (split only independent claims; groups of at most 3 for long lists).
- label_tools.py export not run; waits for claims_A.csv and claims_B.csv.

## 2026-11-25 Segmentation finalized
- Akram's check merged (writing/5_author_tasks/Akram/segmentation_check_FINAL.xlsx; original draft kept as segmentation_review.ORIGINAL.csv). 9 sentences dropped; claims_A.csv = 217 claims (197 test, 20 dev), 112 questions. test_keys passes.
- Set B: rounds 1-3 of review done; round 4 (4 required rows + 1 optional) with Fanan. claims_B.csv not yet created; label_tools export not run.

## 2026-11-26 Set B finalized
- Fanan's edits passed review after 4 rounds (rounds 1-3 rewrote 70, 25 and 5 rows; round 4 final 2). claims_B.csv = 224 claims (112 pairs). Original worksheet kept as setB_worksheet.ORIGINAL.csv.
- Author-written, no AI tools (reported by Fanan on the sheet). Study lead reports R1, R2 and R3 stated they used no AI tools; written confirmations still to be filed with the study records.
- label_tools export not run yet.

## 2026-11-26 Dev calibration passed
- R1 and R2 completed 44 dev claims (20 Set A, 24 Set B). Raw agreement 1.000, kappa 1.000, 0 disagreements, subtypes 44/44 (data/labels_dev/agreement.json). Threshold was >= 0.80. Study lead confirms the R1 file (..._R1_human.xlsx) is R1's original submission and both files reflect the reviewers' own work.
- Small-sample note: B-NHLBI-0000130-7-E (designed addition: "contact sports" is not in the passage) was labelled supported by both reviewers. Kept in Set B as an addition; n=44 so agreement is not a precision estimate. Only 2 of 20 dev Set A claims were unsupported.
- Open: Reviewer information fields (qualification, field, experience, English level) still blank for R1 and R2 on the dev forms; must be collected and R1's qualification disclosed in Methods.

## 2026-11-26 Main labelling round returned
- R1 and R2 each labelled 397 test claims (197 Set A, 200 Set B). Raw agreement 0.950, kappa 0.880, 20 disagreements (18 Set A; 14 involve R1 "unassessable") -> data/labels/agreement.json; R3 adjudication form data/labels/adjudication_form_R3.xlsx (labels hidden).
- Completed forms: data/labels/completed_R1.csv, completed_R2.csv (submitted originals: submitted_R1.xlsx, submitted_R2.xlsx). R2 returned a re-created single-sheet workbook ("MainRound", subtype typed "None"); text columns verified identical to the sent form; converted by hand. Study lead confirms same reviewers/own work.
- Reviewer credentials (from practice forms, per study lead identical to earlier): R1 Master's bioscience, biomedical, 2 y, good; R2 PhD nursing, nurse, 6 y, fluent; R3 PhD, pharmacist, 15 y, fluent.
- Set A yield: only 8 of 197 Set A claims called unsupported by either reviewer (1 by both). Minimum-yield rule (30) expected to trigger a reserve draw; decision pending before any judge output.

## 2026-11-26 R3 adjudication returned; follow-up on Salivary Gland items
- R3 adjudicated the 20 disputed items (data/labels/adjudicated_R3.csv, submitted_R3.xlsx). The workbook had only the Adjudication sheet and empty evidence_span; R3's Reviewer information sheet has NOT been received (credentials taken from R3's earlier form).
- Queried near-identical items: I486761 (A-CancerGov-0000024_8-8-02, "only provides general information about clinical trials...") and I845393 (A-CancerGov-0000024_8-8-01, "does not specifically mention research or clinical trials for Salivary Gland Cancer"). R3 confirmed both original rulings: I486761 unsupported (absent_or_overextended) because the passage goes beyond general trial information by describing radiosensitizers and the claim says "only"; I845393 supported because it is a narrower statement that the passage never names salivary gland cancer.
- Transparency note: this is a borderline distinction. The ruling turns on the word "only" and on one claim being broader; both claims are refusal-type statements about the passage, and the decision on how to treat refusal-type claims (Methods: excluded from scoring) is pending. Rulings retained as returned; sensitivity analysis excluding refusal-type claims is planned.
- gold.csv NOT written (held at study lead's request pending refusal-type decision and reserve draw). Candidate list of refusal-type claims: data/labels/refusal_type_claims.csv.

## 2026-11-26 Gold standard finalized
- Study lead decisions: (1) exclude 17 refusal-type Set A claims (IDs in data/claims/refusal_excluded.csv; 11 supported, 5 unsupported, 1 unassessable by adjudicated/agreed label); keep 3 descriptive claims A-NIDDK-0000128-4-01, A-NIDDK-0000158-13-03, A-NIDDK-0000162-3-02. (2) Reserve draw dropped; Protocol Amendment 4 written (protocol_amendments.md) before any judge output was seen. (3) gold.csv written.
- Excluded IDs: A-CancerGov-0000003_4-4-01, A-CancerGov-0000004_3-4-01, A-CancerGov-0000004_4-2-02, A-CancerGov-0000006_6-5-02, A-NIDDK-0000008-2-01, A-CancerGov-0000024_8-8-01, A-CancerGov-0000024_8-8-02, A-NIDDK-0000049-2-01, A-NIDDK-0000054-14-01, A-NIDDK-0000131-12-02, A-NIDDK-0000131-12-03, A-NIDDK-0000136-7-02, A-NIDDK-0000158-13-02, A-NIDDK-0000162-3-01, A-NIDDK-0000192-8-01, A-NIDDK-0000206-10-01, A-NIDDK-0000206-10-02.
- gold.csv: 380 rows = Set A 180 (175 supported, 5 unsupported) + Set B 200 (98 supported, 102 unsupported: 34 addition, 33 contradiction, 33 strengthening, 2 paraphrases adjudicated unsupported: B-CancerGov-0000006_2-3-S, B-NHLBI-0000131-5-S). gold_excluded.csv lists the 17. test_keys.py passes.
- Correction to an earlier message: Set A after exclusion is 180 claims (197-17), not 177; unsupported rate 5/180 = 2.8% (exact 95% CI 0.9 to 6.4).
- R3 credentials: to be taken from R3's earlier verified form (PhD, pharmacist, 15 y, fluent English) if R3 does not return a Reviewer information tab. Credentials table still needs: R1 Master's bioscience 2 y good; R2 PhD nursing 6 y fluent; R3 as above; Methods wording for R1's qualification against "suitably qualified".
- Methods/Results to update: minimum-yield sentence and the \tbd threshold (replace with Amendment 4), Set B primary / Set A descriptive framing, claim counts (Set A 180 scored + 17 excluded; Set B 200), reviewer agreement (raw 0.950, kappa 0.880 on 397 items), 2 adjudicated-unsupported paraphrases.

## 2026-11-26 Manuscript updated, greedy arm decided, protocol frozen
- Methods/Results edited: abstract, design (Set B primary, Set A descriptive), segmentation (17 refusal exclusions), reviewers and credentials (R1 less experienced, disclosed; no-AI statements), calibration (44 dev claims, agreement 1.0, manual not revised, one missed addition noted), greedy-arm date, call counts (N_A 180, N_B 200, 9,120 planned), minimum-yield paragraph (Amendment 4), class-count table, agreement paragraph. Judge results remain TBD.
- Greedy arm kept; Amendment 5 logged (2026-11-26) before any test judging.
- data/items.csv built (380 items, sha256 adbdfb07...2ef2759). Freeze recorded in data/FREEZE.json and writing/4_notes/protocol_freeze.md. Judges NOT yet run.

## 2026-11-27 judge runs and analysis
- Full matrix run on the MacBook Pro M4 Pro (llama-cpp-python 0.3.38, Metal) per protocol_freeze.md: 6,840 sampled + 2,280 greedy calls, all status ok (100% valid), no duplicate keys, 380 claims x 2 judges x 3 prompts covered. Freeze re-verified (18 files, 0 mismatches) after the runs. Run env: data/models/pilot_env_pip_freeze.txt (venv ~/venvs/medllm).
- H200 package pushed to a private repo but NOT used; no result comes from the H200, so no Amendment 6.
- analysis.py run once: data/results.json (sha256 starts ab75691c019d1cbf). Warnings: Set B self-vs-cross has no self claims (NaN); 11/2000 Set A bootstrap draws had no unsupported claims.

## 2026-11-27 post-freeze audit observation (no change to frozen files)
- A-NIDDK-0000162-3-02 (Set A; "The passage only provides general information about the progression of CKD and its effects on the body."): frozen gold = supported; both judges classed it unsupported in 9/9 sampled conditions (false positive for both under the frozen label). It is one of the 3 descriptive passage-mentioning claims kept after the refusal-type exclusion (Amendment 4). gold.csv NOT altered; reported in the manuscript as an audit observation (if relabelled: Set A sensitivity 1/6 instead of 0/5 per judge; no Set B change).
- Manuscript fill scripts added: code/fill_manuscript.py (results/tables/figures), code/fill_manuscript_final.py (back matter, reproducibility list, related work), code/build_docx.py (Word build, pandoc>=3 --citeproc). Blind switch \blindtrue/\blindfalse in manuscript.tex.

## 2026-11-27 revision after external review
- Effect direction fixed to Qwen minus Llama (+0.176, 95% CI +0.099 to +0.257) in abstract, text, tables, captions.
- Set A wording: "not estimable" replaced by observed 0/5 with exact interval 0-0.522. Greedy Set A per-prompt counts replace the pooled exact interval (same 5 claims judged under 3 prompts).
- Amendment 4 timing and the 17 refusal-type exclusions stated in the main Methods; study framed as controlled evaluation (Set B) plus descriptive Set A.
- New scripts: code/run_exclusion_sensitivity.sh (judges on the 17 excluded claims, data/items_excluded17.csv), code/analysis_exclusion.py, code/fill_exclusion.py, code/build_mjaih_tex.py, code/build_mjaih_docx.py.
- The judge run on the 17 excluded claims is done after the primary analysis and is reported as such.
