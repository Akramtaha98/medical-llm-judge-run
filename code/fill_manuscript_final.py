"""Second manuscript-fill pass: front/back matter, reproducibility, related work, audit note.
Usage: python fill_manuscript_final.py manuscript.tex references.bib   (each anchor must occur once)."""
import sys
tex_path, bib_path = sys.argv[1:3]
tex = open(tex_path, encoding='utf-8').read()
def rep(old, new):
    global tex
    assert tex.count(old) == 1, (tex.count(old), old[:70])
    tex = tex.replace(old, new)

# --- blinding switch -----------------------------------------------------
rep(r"\newcommand{\tbd}[1][]{\textbf{[TBD#1]}}",
    r"""\newcommand{\tbd}[1][]{\textbf{[TBD#1]}}
% Review copy: \blindtrue. Camera-ready or unblinded copy: \blindfalse.
\newif\ifblind \blindtrue
\newcommand{\repourl}{https://github.com/Akramtaha98/medical-llm-judge-run}""")

# --- related work: reused code + literature ------------------------------
rep(r"Tools shared between the two studies are \tbd[: list reused code or components].",
    r"Tools shared between the two studies are \tbd[: list reused code or components, if any].")
rep(r"Searches were run on \tbd[: dates], and the closest papers were compared on question source, annotation unit, human reference, model size, prompt controls and treatment of repeated runs \tbd[: insert results of the search and any additional closely related work].",
    r"""The protocol searches were run on \tbd[: dates of the protocol searches], and a supplementary search of arXiv and the ACL Anthology on 27 November 2026 added the closest work below. The closest papers were compared on question source, annotation unit, human reference, model size, prompt controls and treatment of repeated runs.

MedScore decomposes free-form answers to patient medical questions into condition-aware claims and verifies them against a retrieval corpus, and reports that the resulting factuality score changes with the decomposition method, the verification corpus and the backbone model \cite{huang2026medscore}. Here the decomposition is fixed, the evidence is one supplied passage, and the verifier is compared with adjudicated human labels. MedRAGChecker verifies atomic claims in biomedical retrieval-augmented answers with distilled compact biomedical models and an ensemble verifier, and its authors report that it flags unsupported and contradicted claims \cite{ji2026medragchecker}; our study instead tests untuned general-purpose instruction models, adds controlled edits with known error types, and reports verdict stability. Med-V1 fine-tunes 3B-parameter models for biomedical evidence attribution and reports performance comparable to much larger models \cite{jin2026medv1}, which suggests that task-specific training is a route we did not test. Schroeder and Wood-Doughty argue that a single deterministic judgment can mislead and that a judge can be consistent and still wrong \cite{schroeder2024reliability}; we add a human reference, a medical passage-grounded task, and a breakdown of what stable errors consist of. To our knowledge, none of these works reports paired prompt and seed stability of small open-weight judges against a blinded, adjudicated human reference on passage-grounded patient-education claims, but this statement is limited to the sources identified in our search.""")

# --- methods: models, equivalence ----------------------------------------
rep(r"license and chat template (\tbd[: values]).",
    r"license and chat template. The original releases are Meta-Llama-3-8B-Instruct (Meta Llama 3 Community License) and Qwen2.5-7B-Instruct (Apache 2.0; the quantized Qwen file is a two-part GGUF shard set). Prompts were sent through the chat-completion interface of llama-cpp-python, which applies the chat template stored in each GGUF file. The quantized artifact repository and revision identifiers are \tbd[: Hugging Face repository and commit hash for each GGUF file].")
rep(r"Two investigators independently confirmed that each sentence requests the same decision about the same inputs, and phrasings that could change polarity (for example a negated frame) were excluded \tbd[: result of the check and number of candidate phrasings discarded].",
    r"The three sentences were written to request the same decision about the same inputs, and phrasings that could change polarity (for example a negated frame) were avoided. Equivalence was assessed by inspection within the study team and was not validated empirically or by independent annotation, which is a limitation.")

# --- results: audit observation ------------------------------------------
rep(r"Supplementary Table~S1 lists the",
    r"""\paragraph{Post-freeze audit observation.} One Set A claim (A-NIDDK-0000162-3-02, a statement that the passage ``only provides general information'' about the progression of chronic kidney disease) carries a frozen gold label of supported, yet both judges classed it as unsupported in all nine sampled conditions. It is one of three descriptive claims that mention the passage and were retained after the refusal-type exclusion (Protocol Amendment~4). We noticed it only after the analysis and did not change the frozen gold file; every estimate here uses the frozen label, so the claim counts as a false positive for both judges. Had it been labelled unsupported, Set A sensitivity would have been 1/6 and not 0/5 for each judge, which would not alter the conclusion that Set A sensitivity cannot be estimated, and no Set B result would change. We report it as an audit observation and not as a correction.

Supplementary Table~S1 lists the""")

# --- back matter ---------------------------------------------------------
rep(r"\tbd[: contributions of each author in CRediT roles; blinded in the review copy].",
    r"""\ifblind Author contributions are provided on the title page and are withheld from the review copy.\else Fanan Hikmat Jasim: Set B construction, Data curation, Investigation, Writing -- review and editing. Mohammed Abdulsalam Abbood: Methodology, Supervision, Writing -- review and editing. Akram Taha Zeyad: Conceptualization, Methodology, Software, Formal analysis, Validation, Investigation, Data curation, Visualization, Project administration, Writing -- original draft.\fi""")
rep(r"\tbd[: declaration].", "The authors declare no competing interests.")
rep(r"\tbd[: funding sources, including any scholarship or compute support; or a statement that none was received].",
    "No specific funding was received for this work.")
rep(r"Institutional determination for public-data research and for reviewer participation: \tbd[: determination and reference].",
    r"Institutional determination for public-data research and for reviewer participation: \tbd[: determination or exemption statement and reference number from the institution].")
rep(r"and analysis code are available at \tbd[: repository or archive DOI].",
    r"""and analysis code are available in the study repository (\ifblind link withheld for double-blind review and given on the title page\else \url{\repourl}\fi). The repository contains the full pipeline: corpus construction and item preparation (\texttt{build\_corpus.py}, \texttt{build\_items.py}, \texttt{qkeys.py}), answer generation and claim segmentation (\texttt{run\_generate.py}, \texttt{segment\_claims.py}, \texttt{check\_answers.py}), controlled-set construction (\texttt{make\_setB.py}), the labelling package and tools (\texttt{make\_labelling\_package.py}, \texttt{label\_tools.py}, \texttt{task\_sheets.py}), the judge prompts, parser and runner (\texttt{prompts.py}, \texttt{run\_judges.py}, \texttt{run\_pilot\_and\_full.sh}), the analysis (\texttt{analysis.py} for the primary estimates and \texttt{analysis\_extra.py} for the exploratory failure-pattern analyses), the figure scripts (\texttt{make\_figures.py}, \texttt{make\_result\_figures.py}, \texttt{make\_extra\_figures.py}), and the scripts that insert the computed values into this manuscript (\texttt{fill\_manuscript.py}, \texttt{fill\_manuscript\_final.py}), with the environment listing (llama-cpp-python 0.3.38) and file checksums in the freeze record. Reviewer identities are not released.""")
rep(r"A record of deviations from the protocol is included \tbd[: deviation log].",
    "A record of deviations from the protocol is included in the protocol amendments file (Amendments~1 to 5).")

# --- discussion comparison -----------------------------------------------
rep(r"Comparison with the closest prior work will be added after the literature search \tbd[: compare with closest prior work].",
    r"Relative to prior work, the stability of factuality judgments reported for general-purpose judges \cite{bellibatlu2026judgesense} is consistent with the low disagreement seen here, but our results show that such stability can coexist with substantial missed detections, as argued for LLM judges generally \cite{schroeder2024reliability}. Claim-level medical verifiers have been reported to flag unsupported and contradicted claims \cite{ji2026medragchecker} and small fine-tuned verifiers to approach larger models \cite{jin2026medv1}; these systems differ in training, evidence and data from the untuned 7--8B judges tested here, so our results do not contradict them, and they indicate where an adapted verifier might close the gap on added details, which we did not test.")

open(tex_path, 'w', encoding='utf-8').write(tex)

bib = open(bib_path, encoding='utf-8').read()
add = r"""
@inproceedings{huang2026medscore,
  title = {{MedScore}: Generalizable Factuality Evaluation of Open-ended Long-form Medical Answers by Domain-adapted Claim Decomposition and Verification},
  author = {Huang, Heyuan and DeLucia, Alexandra and Tiyyala, Vijay Murari and Dredze, Mark},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2026},
  year = {2026},
  pages = {14149--14180}
}

@misc{ji2026medragchecker,
  title = {{MedRAGChecker}: Claim-Level Verification for Biomedical Retrieval-Augmented Generation},
  author = {Ji, Yuelyu and Kwak, Min Gu and Zhang, Hang and Wu, Xizhi and Li, Chenyu and Wang, Yanshan},
  year = {2026},
  eprint = {2601.06519},
  archivePrefix = {arXiv}
}

@misc{jin2026medv1,
  title = {{Med-V1}: Small Language Models for Zero-shot and Scalable Biomedical Evidence Attribution},
  author = {Jin, Qiao and Fang, Yin and He, Lauren and Yang, Yifan and Xiong, Guangzhi and Wang, Zhizheng and Wan, Nicholas and Chan, Joey and Comeau, Donald C. and Leaman, Robert and Floudas, Charalampos S. and Zhang, Aidong and Chiang, Michael F. and Peng, Yifan and Lu, Zhiyong},
  year = {2026},
  eprint = {2603.05308},
  archivePrefix = {arXiv}
}

@misc{schroeder2024reliability,
  title = {Can You Trust {LLM} Judgments? Reliability of {LLM}-as-a-Judge},
  author = {Schroeder, Kayla and Wood-Doughty, Zach},
  year = {2024},
  eprint = {2412.12509},
  archivePrefix = {arXiv}
}
"""
open(bib_path, 'a', encoding='utf-8').write(add)
print('ok; tbd left:', tex.count(r'\tbd['))
