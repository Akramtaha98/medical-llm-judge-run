#!/usr/bin/env python3
"""Convert blinded labelling and adjudication forms between CSV (used by label_tools.py) and Excel (for volunteers).

  Reviewer form:
    python code/form_xlsx.py to-xlsx data/labels/form_R1.csv data/labels/form_R1.xlsx
    python code/form_xlsx.py to-csv  returned/form_R1.xlsx   data/labels/form_R1.csv --against data/labels/form_R1.orig.csv
  Adjudication sheet (kind is detected from the sheet name; or pass --kind adjudication):
    python code/form_xlsx.py to-xlsx data/labels/adjudication_sheet.csv data/labels/adjudication_form_R3.xlsx --kind adjudication
    python code/form_xlsx.py to-csv  returned/adjudication_form_R3.xlsx  data/labels/adjudication_sheet.csv

Read-only columns are blind_id, question, passage, claim. Reviewers fill label (or final_label), subtype,
evidence_span and reason (or adjudication_note), with drop-down lists. `to-csv` rejects a missing or invalid label,
an unsupported row without a subtype, and (with --against) any change to the read-only columns. It also warns when
the reviewer code on the "Reviewer information" sheet is not R1, R2 or R3.
"""
import argparse, csv, re, sys
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.worksheet.datavalidation import DataValidation

LABELS = ["supported", "unsupported", "unassessable"]
SUBTYPES = ["contradicted", "absent_or_overextended"]
READONLY = ["blind_id", "question", "passage", "claim"]
KINDS = {  # sheet title, fields, label column, note column
    "labels": ("Labels", READONLY + ["label", "subtype", "evidence_span", "reason"], "label"),
    "adjudication": ("Adjudication", READONLY + ["final_label", "subtype", "evidence_span", "adjudication_note"], "final_label"),
}
WIDTHS = [11, 34, 70, 48, 16, 24, 40, 40]
INFO = [["Reviewer code (R1, R2 or R3 only; given by the study team)", ""], ["Highest qualification", ""],
        ["Field / profession (for example physician, nurse, pharmacist, biomedical scientist)", ""],
        ["Years of clinical or biomedical experience", ""],
        ["English reading proficiency (self-rated: basic / good / fluent)", ""], ["Do not write your name.", ""]]


def kind_of(path_or_wb, forced=None):
    if forced:
        return forced
    return "adjudication" if "Adjudication" in load_workbook(path_or_wb).sheetnames else "labels"


def to_xlsx(src, dst, kind="labels"):
    title, fields, labcol = KINDS[kind]
    rows = list(csv.DictReader(open(src, newline="", encoding="utf-8")))
    wb = Workbook(); ws = wb.active; ws.title = title
    ws.append(fields)
    for r in rows:
        ws.append([r.get(f, "") for f in fields])
    head = PatternFill("solid", fgColor="1F3864"); inp = PatternFill("solid", fgColor="FFF2CC")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = head; c.alignment = Alignment(vertical="center")
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            editable = fields[c.column - 1] not in READONLY
            c.protection = Protection(locked=not editable)
            if editable:
                c.fill = inp
    n = len(rows) + 1
    dv1 = DataValidation(type="list", formula1='"%s"' % ",".join(LABELS), allow_blank=True, showErrorMessage=True,
                         errorTitle="Invalid label", error="Choose supported, unsupported or unassessable.")
    dv2 = DataValidation(type="list", formula1='"%s"' % ",".join(SUBTYPES), allow_blank=True, showErrorMessage=True,
                         errorTitle="Invalid subtype", error="Choose contradicted or absent_or_overextended.")
    ws.add_data_validation(dv1); ws.add_data_validation(dv2)
    dv1.add(f"E2:E{n}"); dv2.add(f"F2:F{n}")
    ws.freeze_panes = "E2"
    ws.protection.sheet = True  # no password: stops accidental edits of the read-only columns
    ws.protection.formatRows = False; ws.protection.formatColumns = False
    info = wb.create_sheet("Reviewer information")
    for r in INFO:
        info.append(r)
    info.column_dimensions["A"].width = 80; info.column_dimensions["B"].width = 40
    wb.save(dst)
    print(f"{len(rows)} rows ({kind}) -> {dst}")


def to_csv(src, dst, against=None, forced=None):
    kind = kind_of(src, forced)
    title, fields, labcol = KINDS[kind]
    wb = load_workbook(src)
    if title not in wb.sheetnames:
        sys.exit(f"sheet '{title}' not found in {src}")
    ws = wb[title]
    head = [c.value for c in ws[1]]
    if head != fields:
        sys.exit(f"unexpected header {head}; expected {fields}")
    rows = [{f: ("" if v is None else str(v).strip()) for f, v in zip(fields, r)} for r in ws.iter_rows(min_row=2, values_only=True)]
    rows = [r for r in rows if r["blind_id"]]
    bad = []
    for r in rows:
        lab = r[labcol].lower()
        if lab not in LABELS:
            bad.append((r["blind_id"], f"missing or invalid {labcol}"))
        elif lab == "unsupported" and r["subtype"] not in SUBTYPES:
            bad.append((r["blind_id"], "unsupported row without a valid subtype"))
        r[labcol] = lab
    if against:
        orig = {r["blind_id"]: r for r in csv.DictReader(open(against, newline="", encoding="utf-8"))}
        if set(orig) != {r["blind_id"] for r in rows}:
            bad.append(("-", "item set differs from the original form"))
        for r in rows:
            o = orig.get(r["blind_id"])
            if o and any(o[f].strip() != r[f] for f in READONLY):
                bad.append((r["blind_id"], "read-only column was changed"))
    if "Reviewer information" in wb.sheetnames:
        code = str(wb["Reviewer information"]["B1"].value or "").strip()
        if not re.fullmatch(r"R[1-3]", code):
            print(f"WARNING: reviewer code is '{code}'; use R1, R2 or R3 only (fix it in the record, not in the data)")
    if bad:
        for b in bad[:20]:
            print("PROBLEM:", *b)
        sys.exit(f"{len(bad)} problem(s); ask the reviewer to fix them before use")
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} rows ({kind}) -> {dst}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["to-xlsx", "to-csv"]); ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--against"); ap.add_argument("--kind", choices=list(KINDS))
    a = ap.parse_args()
    if a.cmd == "to-xlsx":
        to_xlsx(a.src, a.dst, a.kind or "labels")
    else:
        to_csv(a.src, a.dst, a.against, a.kind)
