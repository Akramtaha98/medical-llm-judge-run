#!/usr/bin/env python3
"""Build the volunteer labelling package: writing/labelling_guide.docx and writing/practice_form.xlsx.

  python code/make_labelling_package.py --out writing

The guide is anonymous: no author names, no model names, no hypotheses. All examples and practice items use
invented passages, not study text. The practice answer key is on the last page of the guide.
"""
import argparse, csv, os, tempfile
from docx import Document
from docx.enum.text import WD_BREAK
from docx.shared import Pt, Cm, RGBColor
import form_xlsx

EX_Q = "What is iron-deficiency anemia and how is it managed?"
EX_P = ("Iron-deficiency anemia happens when the body does not have enough iron to make hemoglobin. Common signs are "
        "tiredness, pale skin and shortness of breath. Doctors often check blood levels of ferritin. Many adults can raise "
        "their iron by eating more iron-rich foods and, if the doctor advises, taking iron supplements for several months. "
        "Pregnant women need more iron than other adults.")
EXAMPLES = [
    ("Iron-deficiency anemia occurs when the body lacks enough iron to produce hemoglobin.", "Supported",
     "Same meaning as the first sentence. Evidence span: \"does not have enough iron to make hemoglobin\"."),
    ("Tiredness and pale skin are common signs.", "Supported", "Both signs are listed in the second sentence."),
    ("Doctors only use ferritin tests to diagnose it.", "Unsupported: absent_or_overextended",
     "The passage says doctors \"often check\" ferritin. \"Only\" and \"to diagnose\" go beyond it."),
    ("Everyone with the condition must take iron supplements.", "Unsupported: absent_or_overextended",
     "The passage says \"many adults\" can raise iron through food and supplements only \"if the doctor advises\"."),
    ("Pregnant women need less iron than other adults.", "Unsupported: contradicted",
     "The last sentence says the opposite. Evidence span: \"need more iron than other adults\"."),
    ("Vitamin C helps the body absorb iron.", "Unsupported: absent_or_overextended",
     "This may be true in general, but the passage never says it. Absence from the passage means unsupported."),
    ("Children need more iron than adults.", "Unsupported: absent_or_overextended",
     "The passage says nothing about children."),
    ("It can also cause that.", "Unassessable",
     "\"It\" and \"that\" have no clear referent, so the statement cannot be checked."),
]

PRACTICE_Q = "What is high blood pressure and how is it treated?"
PRACTICE_P = ("High blood pressure usually has no symptoms. The only way to know is to measure it. A reading of 130/80 mmHg "
              "or higher is considered high in adults. Lifestyle changes such as eating less salt, being physically active "
              "and limiting alcohol can lower blood pressure. Some people also need medicine. Left untreated, high blood "
              "pressure can damage the heart, kidneys and blood vessels.")
PRACTICE = [
    ("High blood pressure usually causes no symptoms.", "supported", "", "Sentence 1."),
    ("A reading below 130/80 mmHg is considered high in adults.", "unsupported", "contradicted",
     "The passage says 130/80 or higher is high."),
    ("Reducing salt intake can lower blood pressure.", "supported", "", "Eating less salt is listed."),
    ("Everyone with high blood pressure needs medicine.", "unsupported", "absent_or_overextended",
     "Only \"some people\" need medicine."),
    ("Exercising for 30 minutes a day lowers blood pressure.", "unsupported", "absent_or_overextended",
     "Being active is mentioned, but the 30-minute figure is not."),
    ("Untreated high blood pressure can damage the kidneys.", "supported", "", "Last sentence."),
    ("It affects them more often.", "unassessable", "", "No clear referent for \"It\" or \"them\"."),
    ("Smoking raises the risk of heart disease.", "unsupported", "absent_or_overextended",
     "True in general, but the passage does not say it."),
]


def shade(cell, hexcolor):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcolor); tcPr.append(sh)


def table(doc, header, rows, widths):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"; t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; shade(c, "D9E2F3")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)
    doc.add_paragraph()
    return t


def numbered(d, items):
    for i, t in enumerate(items, 1):
        p = d.add_paragraph(f"{i}.  {t}"); p.paragraph_format.left_indent = Cm(0.9); p.paragraph_format.first_line_indent = Cm(-0.6)


def build_guide(path):
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2.2); s.top_margin = s.bottom_margin = Cm(2.0)
    d.add_heading("Claim Labelling Guide for Volunteer Reviewers", 0)
    p = d.add_paragraph(); r = p.add_run("Please read this guide completely before you open your file. Keep it open while you work."); r.italic = True

    d.add_heading("1. What this is", 1)
    d.add_paragraph("You are helping build a human reference standard for a research study on automatic checking of health "
                    "information. For each row you will decide whether one short statement (a claim) is supported by a "
                    "passage taken from a public health-information page. Your labels will be compared with those of other "
                    "volunteers and used as the reference. There are no right or wrong people here: we need your honest, "
                    "independent reading of the passage.")

    d.add_heading("2. What you receive", 1)
    d.add_paragraph("An Excel file with one row per claim. The grey columns are read-only:")
    for t in ["blind_id: a random item number. It carries no information.",
              "question: the question the passage answers. It gives context only.",
              "passage: the evidence. This is the only source you may use.",
              "claim: the statement you judge."]:
        d.add_paragraph(t, style="List Bullet")
    d.add_paragraph("You fill the yellow columns: label (drop-down), subtype (drop-down, only for unsupported), evidence_span "
                    "and reason.")

    d.add_heading("3. Ground rules", 1)
    numbered(d, [
        "Work alone. Do not discuss any item with anyone, including the other volunteers, until the study team says so.",
        "Use only the passage. Do not search the internet, do not use books or notes, and do not use AI tools or translators.",
        "Do not use your own medical knowledge to fill gaps. A claim can be true in real life and still be unsupported by the passage.",
        "Judge every claim by itself, in the order the rows come. Do not try to guess where a claim came from or who wrote it.",
        "Label every row. If unsure, use the decision steps in Section 5, then give your best label and write the doubt in reason.",
        "Do not edit, delete, sort or add rows. Save often and work in sessions of about one hour.",
        "Keep the file and its content confidential. Do not copy or share it."])

    d.add_heading("4. The three labels", 1)
    table(d, ["Label (subtype)", "Use it when", "What to write"], [
        ["supported", "The passage states the claim, or the claim follows from the passage without any outside assumption, "
                      "and every qualifier in the claim (how often, how many, who, when, how certain) also holds.",
         "evidence_span: copy the shortest part of the passage that supports it."],
        ["unsupported + contradicted", "The passage gives information that conflicts with the claim.",
         "evidence_span: copy the conflicting part."],
        ["unsupported + absent_or_overextended", "The passage does not give enough information, or the claim makes the passage "
                                                  "stronger, wider or more precise (certainty, scope, timing, numbers, who is affected).",
         "reason: say what is missing or overstated."],
        ["unassessable", "The claim is unclear after reading it carefully (for example \"it\" has no clear referent) or is not a "
                         "checkable statement. Do NOT use this because the passage lacks the information: a clear claim that is "
                         "missing from the passage is unsupported.", "reason: say what is unclear."]],
          [4.8, 8.0, 3.8])

    d.add_heading("5. Decision steps", 1)
    numbered(d, ["Read the question, then the whole passage.",
              "Read the claim. Can you tell exactly what it says? If not, it is unassessable.",
              "Split the claim mentally into its parts and qualifiers (numbers, \"all\", \"only\", \"always\", \"can\" versus \"will\", who, when).",
              "Check every part against the passage. If every part is stated or directly follows, it is supported.",
              "If any part conflicts with the passage, it is unsupported: contradicted.",
              "If any part is missing, stronger, wider or more precise than the passage, it is unsupported: absent_or_overextended.",
              "If one part is supported and another is not, the whole claim is unsupported."])

    d.add_heading("6. Worked examples", 1)
    d.add_paragraph("Question: " + EX_Q)
    q = d.add_paragraph(); q.add_run("Passage (invented for training): ").bold = True; q.add_run(EX_P)
    table(d, ["Claim", "Correct label", "Why"], [[c, l, w] for c, l, w in EXAMPLES], [5.6, 3.6, 7.4])

    d.add_heading("7. Practice round (do this first)", 1)
    d.add_paragraph("Open practice_form.xlsx and label all 8 rows using only this guide. Then return the file to the study "
                    "team. Do not look at the answer key on the last page until you have finished. After the practice round "
                    "the team may ask you to label a short set of calibration items. You may be invited to one short "
                    "discussion of those items. That is the only discussion allowed before the main task.")

    d.add_heading("8. The main task", 1)
    d.add_paragraph("You will receive your file by a private link or email. It contains several hundred rows. Expect about "
                    "1 to 2 minutes per row. Return the completed file by the date given by the study team. You may take breaks; "
                    "your answers are saved in the file.")
    d.add_heading("Adjudicator only", 2)
    d.add_paragraph("If you are the adjudicator, you will receive a different, shorter sheet that contains only items where "
                    "the first two reviewers disagreed. Their labels are hidden. Apply the same rules, then fill final_label, "
                    "subtype and adjudication_note.")

    d.add_heading("9. Your participation", 1)
    d.add_paragraph("Taking part is voluntary and you may stop at any time. We record only your anonymous reviewer code and a "
                    "short professional background note (see the Reviewer information sheet in your file). Your labels are "
                    "analysed together with those of the other reviewers and may appear in anonymised form in publications "
                    "and shared data. You will be acknowledged by role unless you ask otherwise. Questions: [study contact email, "
                    "to be added by the study team].")

    d.add_page_break()
    d.add_heading("Practice answer key (look only after finishing practice_form.xlsx)", 1)
    d.add_paragraph("Question: " + PRACTICE_Q)
    q = d.add_paragraph(); q.add_run("Passage (invented): ").bold = True; q.add_run(PRACTICE_P)
    table(d, ["#", "Claim", "Correct label", "Note"],
          [[str(i + 1), c, (l + (": " + s if s else "")), n] for i, (c, l, s, n) in enumerate(PRACTICE)], [0.8, 6.2, 4.2, 5.4])
    d.save(path)


def build_practice(path):
    rows = [{"blind_id": f"P{i + 1:02d}", "question": PRACTICE_Q, "passage": PRACTICE_P, "claim": c,
             "label": "", "subtype": "", "evidence_span": "", "reason": ""} for i, (c, *_r) in enumerate(PRACTICE)]
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=form_xlsx.KINDS["labels"][1]); w.writeheader(); w.writerows(rows); tmp = f.name
    form_xlsx.to_xlsx(tmp, path)
    os.remove(tmp)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="writing"); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    build_guide(os.path.join(a.out, "labelling_guide.docx")); build_practice(os.path.join(a.out, "practice_form.xlsx"))
    print("wrote labelling_guide.docx and practice_form.xlsx in", a.out)
