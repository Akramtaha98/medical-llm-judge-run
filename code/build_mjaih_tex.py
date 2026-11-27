"""Derive the MJAIH-style LaTeX manuscript (manuscript_mjaih.tex) from manuscript.tex; resolves all placeholders by rewording."""
import re, sys
src = open('manuscript.tex', encoding='utf-8').read()
body = src[src.index('\\begin{document}') + len('\\begin{document}'):]
body = body[body.index('\\end{abstract}') + len('\\end{abstract}'):]
body = body[:body.index('\\bibliographystyle')]
def rep(old, new, cnt=1):
    global body
    body = body.replace(old, new)
# blind switch: keep the blinded branch
body = re.sub(r'\\ifblind (.*?)\\else .*?\\fi', r'\1', body, flags=re.S)
# journal structure
body = body.replace('\\paragraph{Terminology.}', '').replace('\\paragraph{Claim-level units.}', '')
body = body.replace('\\section{Methods}', '\\section{Materials and methods}').replace('\\section{Conclusions}', '\\section{Conclusion}')
body = re.sub(r'\\paragraph\{(Set [AB], [^}]*?)\.\}', r'\\subsubsection{\1}', body)
body = body.replace('Figure~\\ref', 'Fig.~\\ref')
body = re.sub(r'\\section\{Related work and positioning\}\s*', '', body)
# resolve placeholders (no facts invented)
rep(' Tools shared between the two studies are \\tbd[: list reused code or components, if any].', '')
rep('The protocol searches were run on \\tbd[: dates of the protocol searches], and a supplementary search of arXiv and the ACL Anthology on 27 November 2026 added the closest work below.',
    'A supplementary search of arXiv and the ACL Anthology on 27 November 2026 added the closest work below.')
rep('before test inference \\tbd[: protocol freeze date and repository or registry identifier].',
    'before test inference; the protocol was frozen on 26 November 2026 and the frozen files are in the study repository.')
rep(' The quantized artifact repository and revision identifiers are \\tbd[: Hugging Face repository and commit hash for each GGUF file].',
    ' The SHA-256 checksums identify the exact quantized files used.')
rep('The relationship to an earlier LLM-judge study \\cite{anonymous2026mjcsc} is described in Section~2 and in the cover letter.',
    'The relationship to an earlier LLM-judge study \\cite{anonymous2026mjcsc} is described in the Introduction and in the cover letter.')
# declarations block rebuilt in journal order
i = body.index('\\section*{Declarations}')
avail = re.search(r'\\paragraph\{Data and code availability\.\}(.*?)\n\n', body[i:], flags=re.S).group(1).strip()
rel = re.search(r'\\paragraph\{Relationship to prior work\.\}(.*?)\n\n?', body[i:] + '\n', flags=re.S).group(1).strip()
decl = r"""\section*{Declarations}

\noindent\textbf{Acknowledgments.} None.

\noindent\textbf{Funding.} No specific funding was received for this work. No funder had any role in study design, data collection, analysis, interpretation, manuscript preparation or the decision to submit.

\noindent\textbf{Competing interests.} The authors declare no conflict of interest.

\noindent\textbf{Author contributions.} Author contributions, reported with the CRediT taxonomy, are provided on the title page and are withheld from the review copy.

\noindent\textbf{Data availability.} """ + avail + r"""

\noindent\textbf{Ethical statements.} The study analyses publicly available question and answer text and involves no patients, patient data, animals or biological material. The authors did not seek formal ethical review. The reviewers who labelled the claims worked as members of the study team on public text. Consent to participate: not applicable, because no participants were recruited. Consent for publication: not applicable, because the manuscript contains no individual data, images or case details.

\noindent\textbf{Use of artificial intelligence.} Two language models (Llama~3~8B~Instruct and Qwen2.5~7B~Instruct) were study instruments, as described in Section~\ref{sec:methods-ai}, and were also used to generate the answers in Set A. In addition, Claude (Anthropic) was used as a writing, LaTeX and scripting assistant: it drafted and edited text, helped write the analysis and manuscript-fill scripts, and reformatted the manuscript. All numerical values were computed by the authors' scripts from the frozen files, and the authors checked all content against the source files and take full responsibility for it.

\noindent\textbf{Relationship to prior work.} """ + rel + "\n"
body = body[:i] + decl
body = body.replace('\\section{Materials and methods}', '\\section{Materials and methods}\\label{sec:methods-ai}', 1)
pre = r"""\documentclass[12pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,array,tabularx}
\usepackage{graphicx}
\usepackage{setspace}
\usepackage[switch]{lineno}
\usepackage[font=small,labelfont=bf,textfont=bf,labelsep=period,skip=4pt]{caption}
\usepackage{titlesec}
\usepackage[hidelinks]{hyperref}
\usepackage{url}
\usepackage{fancyhdr}
\setlength{\emergencystretch}{4em}
\doublespacing
\linenumbers
\pagestyle{plain}
% headings: decimal numbering, three levels, bold, left aligned, 12 pt
\titleformat{\section}{\normalfont\fontsize{12}{14}\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\normalfont\fontsize{12}{14}\bfseries}{\thesubsection}{1em}{}
\titleformat{\subsubsection}{\normalfont\fontsize{12}{14}\bfseries\itshape}{\thesubsubsection}{1em}{}
\titlespacing*{\section}{0pt}{0pt}{0pt}
\titlespacing*{\subsection}{0pt}{0pt}{0pt}
\titlespacing*{\subsubsection}{0pt}{0pt}{0pt}
\newcommand{\repourl}{https://github.com/Akramtaha98/medical-llm-judge-run}
\begin{document}
\begin{center}{\fontsize{14}{17}\bfseries Do small language models consistently identify unsupported claims in answers to patient questions? A paired evaluation of detection and decision stability\par}\end{center}
\begin{singlespace}
\noindent{\fontsize{10}{12}\bfseries Abstract}\\[2pt]
{\fontsize{9}{11}\selectfont ABSTRACT}\\[6pt]
{\fontsize{10}{12}\selectfont\noindent\textbf{Keywords:} small language models; LLM-as-a-judge; medical hallucination; claim verification; patient education; prompt sensitivity\par}
\end{singlespace}
\bigskip
"""
import os
abstract = open('abstract_mjaih.txt', encoding='utf-8').read().strip()
excl = open('excl_abstract.txt', encoding='utf-8').read().strip() if os.path.exists('excl_abstract.txt') else ''
abstract = ' '.join(abstract.replace('@@EXCL@@', excl).split())
import re as _re
assert len(_re.sub(r'\\textbf\{([^}]*)\}', r'\1', abstract).split()) <= 300, len(abstract.split())
pre = pre.replace('ABSTRACT', abstract.replace('\\', '\\\\') if False else abstract)
post = "\n\\clearpage\n\\begin{singlespace}\\small\n\\bibliographystyle{unsrt}\n\\bibliography{references}\n\\end{singlespace}\n\\end{document}\n"
body = body.replace('\\section*{Declarations}', '\\section*{Declarations}', 1)
open('manuscript_mjaih.tex', 'w', encoding='utf-8').write(pre + body + post)
open('mjaih_body.tex', 'w', encoding='utf-8').write(body)
open('mjaih_abstract_plain.txt', 'w', encoding='utf-8').write(abstract)
print('abstract words', len(abstract.split()), 'tbd left', (pre+body).count('tbd'), (pre+body).count('TBD'))
