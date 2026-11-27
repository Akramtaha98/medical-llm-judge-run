"""Build the anonymized Word manuscript from manuscript.tex (pandoc >= 3 with --citeproc), then tidy tables.
Usage: python build_docx.py manuscript.tex references.bib reference.docx out.docx   (pandoc must be on PATH)"""
import re, subprocess, sys, tempfile, os
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
tex_in, bib, ref, out = sys.argv[1:5]
t = open(tex_in, encoding='utf-8').read()
t = t.replace('\\resizebox{\\textwidth}{!}{', '')
for lab in ['tab:detect', 'tab:fail']:
    i = t.index('\\label{%s}' % lab); e = t.index('\\end{tabular}', i) + len('\\end{tabular}')
    assert t[e] == '}'; t = t[:e] + t[e+1:]
t = re.sub(r'\\ifblind (.*?)\\else .*?\\fi', r'\1', t, flags=re.S)      # blind (review) copy
t = t.replace('\\newif\\ifblind \\blindtrue', '')
t = t.replace('\\text{\\quad\\quad}', '\\quad\\quad').replace('\\big(', '(').replace('\\big)', ')')
t = t.replace('$^{\\dagger}$', '\u2020')
# numbered captions
cnt = {'table': 0, 'figure': 0}
def num(m):
    env = m.group(1); cnt[env] += 1
    body = m.group(0)
    return body.replace('\\caption{', '\\caption{%s %d. ' % (env.capitalize(), cnt[env]), 1)
t = re.sub(r'\\begin\{(table|figure)\}.*?\\end\{\1\}', num, t, flags=re.S)
d = tempfile.mkdtemp(); p = os.path.join(d, 'm.tex'); open(p, 'w', encoding='utf-8').write(t)
subprocess.run(['pandoc', p, '-f', 'latex', '--bibliography=' + bib, '--citeproc', '--reference-doc=' + ref,
                '--resource-path=' + os.path.dirname(os.path.abspath(tex_in)), '-o', out], check=True)
doc = Document(out)
for tbl in doc.tables:
    tp = tbl._tbl.tblPr
    for el in tp.findall(qn('w:tblW')): tp.remove(el)
    w = OxmlElement('w:tblW'); w.set(qn('w:w'), '5000'); w.set(qn('w:type'), 'pct'); tp.append(w)
    for el in tp.findall(qn('w:tblLayout')): tp.remove(el)
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'autofit'); tp.append(lay)
    grid = tbl._tbl.find(qn('w:tblGrid'))
    ncol = len(tbl.columns)
    # width weights by longest cell text in each column
    wts = []
    for ci in range(ncol):
        L = max((len(r.cells[ci].text) for r in tbl.rows if ci < len(r.cells)), default=1)
        wts.append(min(max(L, 6), 40))
    tot = sum(wts)
    for ci, g in enumerate(grid.findall(qn('w:gridCol'))): g.set(qn('w:w'), str(int(9000 * wts[ci] / tot)))
    for r in tbl.rows:
        for ci, c in enumerate(r.cells):
            tc = c._tc.get_or_add_tcPr()
            for el in tc.findall(qn('w:tcW')): tc.remove(el)
            cw = OxmlElement('w:tcW'); cw.set(qn('w:w'), str(int(5000 * wts[ci] / tot))); cw.set(qn('w:type'), 'pct'); tc.insert(0, cw)
            for para in c.paragraphs:
                for run in para.runs: run.font.size = Pt(8.5)
doc.save(out)
