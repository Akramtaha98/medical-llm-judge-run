#!/usr/bin/env python3
"""Excel task sheets for the two author tasks (segmentation check, Set B edits).

  python code/task_sheets.py to-xlsx seg  --csv data/claims/segmentation_review.csv --out seg.xlsx
  python code/task_sheets.py to-xlsx setb --csv data/claims/setB_worksheet.csv      --out setb.xlsx
  python code/task_sheets.py to-csv  seg  --xlsx seg.xlsx  --against data/claims/segmentation_review.csv --out merged.csv
  python code/task_sheets.py to-csv  setb --xlsx setb.xlsx --against data/claims/setB_worksheet.csv      --out merged.csv

to-csv copies ONLY the editable columns into a copy of the original CSV (matched by key) and refuses to
continue if a read-only value differs, a key is missing or duplicated, or an entry is invalid.
"""
import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qkeys import qkey
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.worksheet.datavalidation import DataValidation

HEAD = PatternFill("solid", fgColor="1F3864"); RO = PatternFill("solid", fgColor="EDEDED"); ED = PatternFill("solid", fgColor="FFF2CC")
WRAP = Alignment(wrap_text=True, vertical="top")

EDIT_HELP = {
    "contradiction": "CONTRADICTION: change the paraphrase so it directly conflicts with the passage (reverse a direction, swap a quantity or negate a stated fact). Change as little as possible.",
    "addition": "ADDITION: add one plausible, specific detail that the passage does NOT state (a number, cause, group or treatment). The rest must stay supported.",
    "strengthening": "STRENGTHENING: make the claim more certain or wider than the passage allows (may -> will, some -> all, adults -> everyone, often -> always).",
}

SPECS = {
    "seg": dict(key="claim_id", sheet="Segmentation",
                ro=[("claim_id", 24), ("split", 8), ("auto_flag", 20), ("question", 38), ("full_answer", 60), ("original_span", 50), ("claim_text", 50)],
                ed=[("ok", 8), ("corrected_text", 55), ("note", 30)]),
    "setb": dict(key="question_id", sheet="SetB",
                 ro=[("question_id", 22), ("split", 8), ("edit_type", 14), ("what_to_do", 48), ("question", 34), ("passage", 80)],
                 ed=[("supported_paraphrase", 55), ("edited_claim", 55), ("builder_note", 28)]),
}


def _context(kind, rows):
    """Add read-only context columns (question, full answer, instructions)."""
    if kind == "seg":
        sel = {qkey(r["source"], r["question_id"]): r for r in csv.DictReader(open("data/corpus/selected.csv", newline="", encoding="utf-8"))}
        ans = {}
        for l in open("data/setA/answers.jsonl", encoding="utf-8"):
            if l.strip():
                a = json.loads(l); ans[qkey(a["source"], a["question_id"])] = a["answer"]
        for r in rows:
            r["question"] = sel[r["question_id"]]["question"]; r["full_answer"] = ans[r["question_id"]]
        flagged = [r for r in rows if r["auto_flag"]]
        return flagged + [r for r in rows if not r["auto_flag"]]
    for r in rows:
        r["what_to_do"] = EDIT_HELP[r["edit_type"]]
    return rows


def to_xlsx(kind, csv_path, out):
    spec = SPECS[kind]
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    rows = _context(kind, rows)
    cols = spec["ro"] + spec["ed"]
    wb = Workbook(); ws = wb.active; ws.title = spec["sheet"]
    extra = [("words_para", 11), ("words_edit", 11)] if kind == "setb" else []
    for j, (c, w) in enumerate(cols + extra, 1):
        cell = ws.cell(1, j, c); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = HEAD; cell.alignment = WRAP
        ws.column_dimensions[cell.column_letter].width = w
    nro = len(spec["ro"])
    for i, r in enumerate(rows, 2):
        for j, (c, _) in enumerate(cols, 1):
            cell = ws.cell(i, j, r.get(c, "")); cell.alignment = WRAP
            cell.fill = RO if j <= nro else ED
            cell.protection = Protection(locked=j <= nro)
        if kind == "setb":
            pi, ei = cols.index(("supported_paraphrase", 55)) + 1, cols.index(("edited_claim", 55)) + 1
            for k, ci in ((len(cols) + 1, pi), (len(cols) + 2, ei)):
                L = ws.cell(i, ci).column_letter
                ws.cell(i, k, f'=IF(LEN(TRIM({L}{i}))=0,"",LEN(TRIM({L}{i}))-LEN(SUBSTITUTE(TRIM({L}{i})," ",""))+1)')
        ws.row_dimensions[i].height = 150 if kind == "setb" else 110
    ws.freeze_panes = ws.cell(2, 2)
    ws.auto_filter.ref = ws.dimensions
    if kind == "seg":
        dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=True); ws.add_data_validation(dv)
        L = ws.cell(1, nro + 1).column_letter; dv.add(f"{L}2:{L}{len(rows) + 1}")
    ws.protection.sheet = True  # no password: only locked (grey) cells are protected
    ws.protection.autoFilter = False; ws.protection.sort = False
    info = wb.create_sheet("Reviewer information")
    for i, (a, b) in enumerate([("Name", ""), ("Date completed", ""), ("Time spent (hours)", ""),
                                ("Used any AI tool to help? (Yes/No)", ""), ("Notes", "")], 1):
        info.cell(i, 1, a).font = Font(bold=True); info.cell(i, 2, b).fill = ED
    info.column_dimensions["A"].width = 36; info.column_dimensions["B"].width = 40
    wb.save(out); print(f"{len(rows)} rows -> {out}")


def to_csv(kind, xlsx, against, out):
    spec = SPECS[kind]; key = spec["key"]
    orig = list(csv.DictReader(open(against, newline="", encoding="utf-8")))
    fields = list(orig[0].keys())
    ws = load_workbook(xlsx, data_only=True)[spec["sheet"]]
    head = [c.value for c in ws[1]]
    got = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(head, row))
        if d.get(key) in (None, ""): continue
        if d[key] in got: sys.exit(f"duplicate key in sheet: {d[key]}")
        got[d[key]] = {k: ("" if v is None else str(v)) for k, v in d.items()}
    ok_keys = {r[key] for r in orig}
    if set(got) != ok_keys:
        sys.exit(f"keys differ: missing {sorted(ok_keys - set(got))[:3]}, unknown {sorted(set(got) - ok_keys)[:3]}")
    errs = []
    for r in orig:
        g = got[r[key]]
        for c in fields:
            if c in [x for x, _ in spec["ed"]] or c not in g: continue
            if g[c].strip() != r[c].strip(): errs.append(f"{r[key]}: read-only column '{c}' was changed")
        for c, _ in spec["ed"]: r[c] = g[c].strip()
        if kind == "seg":
            ok, ct = r["ok"].upper(), r["corrected_text"]
            if ok not in ("Y", "N"): errs.append(f"{r[key]}: ok must be Y or N")
            elif ok == "N" and not ct: errs.append(f"{r[key]}: ok=N needs corrected_text or DROP")
            r["ok"] = ok
        else:
            p, e = r["supported_paraphrase"], r["edited_claim"]
            if not p or not e: errs.append(f"{r[key]}: both claims are required")
            elif p.lower() == e.lower(): errs.append(f"{r[key]}: edited claim identical to paraphrase")
            else:
                a, b = len(p.split()), len(e.split())
                if max(a, b) > 1.5 * min(a, b) + 3: print(f"warning {r[key]}: length mismatch ({a} vs {b} words)")
    if errs:
        print("\n".join(errs[:40])); sys.exit(f"{len(errs)} problems; fix the sheet and retry")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(orig)
    print(f"{len(orig)} rows merged -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["to-xlsx", "to-csv"]); ap.add_argument("kind", choices=["seg", "setb"])
    ap.add_argument("--csv"); ap.add_argument("--xlsx"); ap.add_argument("--against"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    to_xlsx(a.kind, a.csv, a.out) if a.cmd == "to-xlsx" else to_csv(a.kind, a.xlsx, a.against, a.out)
