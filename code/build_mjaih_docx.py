"""Build the MJAIH-formatted anonymized Word manuscript from manuscript.tex.
Journal rules (map.researchcommons.org/mjaih/author_guidelines.html): Times New Roman, double spacing, justified, single column,
continuous line numbers, page numbers, decimal headings (3 levels), numeric bracket citations in order of appearance,
abstract <= 300 words (9 pt), keywords (10 pt), title 14 pt bold centred, table titles above and figure captions below (9 pt bold),
no vertical table lines, Introduction without subheadings, Declarations before References.
Usage: python build_mjaih_docx.py manuscript.tex references.bib ieee.csl out.docx   (pandoc >= 3 on PATH)"""
import re, subprocess, sys, os, tempfile, copy
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
tex_in, bib, csl, out = sys.argv[1:5]

import re as _re
_abs = open(os.path.join(os.path.dirname(os.path.abspath(tex_in)), 'mjaih_abstract_plain.txt'), encoding='utf-8').read()
_abs = _abs.replace('\\%', '%').replace('$-$', '\u2212')
_parts = _re.split(r'\\textbf\{([^}]*:)\}', _abs)
ABSTRACT = [(_parts[i] + ' ', _parts[i+1].strip() + ' ') for i in range(1, len(_parts), 2)]
KEYWORDS = "small language models; LLM-as-a-judge; medical hallucination; claim verification; patient education; prompt sensitivity"
TITLE = "Do small language models consistently identify unsupported claims in answers to patient questions? A paired evaluation of detection and decision stability"
nwords = sum(len((a+b).split()) for a, b in ABSTRACT)
assert nwords <= 300, nwords
print('abstract words', nwords)

t = open(os.path.join(os.path.dirname(os.path.abspath(tex_in)), 'mjaih_body.tex'), encoding='utf-8').read() + '\n\\section*{References}\n'
t = _re.sub(r'\\paragraph\{([^}]*)\}', r'\\par\\medskip\\noindent\\textbf{\1}', t)
# ---- generic cleanups (as build_docx.py) ----
t = t.replace('\\resizebox{\\textwidth}{!}{', '')
for lab in ['tab:detect', 'tab:fail']:
    a = t.index('\\label{%s}' % lab); e = t.index('\\end{tabular}', a) + len('\\end{tabular}')
    assert t[e] == '}'; t = t[:e] + t[e+1:]
t = re.sub(r'\\ifblind (.*?)\\else .*?\\fi', r'\1', t, flags=re.S)
t = t.replace('\\newif\\ifblind \\blindtrue', '')
t = t.replace('\\text{\\quad\\quad}', '\\quad\\quad').replace('\\big(', '(').replace('\\big)', ')')
t = t.replace('$^{\\dagger}$', '\u2020')
cnt = {'table': 0, 'figure': 0}
def num(m):
    env = m.group(1); cnt[env] += 1
    lab = 'Table' if env == 'table' else 'Fig.'
    return m.group(0).replace('\\caption{', '\\caption{%s %d. ' % (lab, cnt[env]), 1)
t = re.sub(r'\\begin\{(table|figure)\}.*?\\end\{\1\}', num, t, flags=re.S)
d = tempfile.mkdtemp(); p = os.path.join(d, 'm.tex'); open(p, 'w', encoding='utf-8').write(t)
raw = os.path.join(d, 'raw.docx')
subprocess.run(['pandoc', p, '-f', 'latex', '--number-sections', '--bibliography=' + bib, '--csl=' + csl, '--citeproc',
                '--resource-path=' + os.path.dirname(os.path.abspath(tex_in)), '-o', raw], check=True)

# ---- Word post-processing ----
doc = Document(raw)
TNR = 'Times New Roman'
def setfont(style, size=None, bold=None, italic=None, color=True):
    f = style.font; f.name = TNR
    rpr = style.element.get_or_add_rPr(); rf = rpr.find(qn('w:rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rpr.append(rf)
    for a in ('ascii', 'hAnsi', 'cs', 'eastAsia'): rf.set(qn('w:' + a), TNR)
    for a in ('asciiTheme', 'hAnsiTheme', 'cstheme', 'eastAsiaTheme'):
        if rf.get(qn('w:' + a)) is not None: del rf.attrib[qn('w:' + a)]
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    if color: f.color.rgb = RGBColor(0, 0, 0)
for st in doc.styles:
    if st.type == 1:  # paragraph
        try: setfont(st)
        except Exception: pass
body_styles = ['Normal', 'Body Text', 'First Paragraph', 'Compact']
for n in body_styles:
    s = doc.styles[n]; setfont(s, 12)
    pf = s.paragraph_format; pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE; pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_before = Pt(0); pf.space_after = Pt(0)
for n, sz in (('Heading 1', 12), ('Heading 2', 12), ('Heading 3', 12)):
    s = doc.styles[n]; setfont(s, sz, bold=True, italic=(n == 'Heading 3'))
    pf = s.paragraph_format; pf.alignment = WD_ALIGN_PARAGRAPH.LEFT; pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    pf.space_before = Pt(0); pf.space_after = Pt(0); pf.keep_with_next = True
for n in ('Image Caption', 'Table Caption', 'Captioned Figure'):
    if n in [s.name for s in doc.styles]:
        s = doc.styles[n]; setfont(s, 9, italic=False)
        s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE; s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.space_before = Pt(6); s.paragraph_format.space_after = Pt(6)
if 'Bibliography' in [s.name for s in doc.styles]:
    s = doc.styles['Bibliography']; setfont(s, 10)
    s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE; s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    s.paragraph_format.space_after = Pt(3)
# captions: bold title sentence, rest regular
def bold_caption(par):
    txt = par.text
    m = re.match(r'^((?:Table|Fig\.) \d+\.\s+.+?[a-z0-9\)\]]\.)(\s|$)', txt)
    cut = len(m.group(1)) if m else len(txt)
    runs = par.runs; pos = 0
    for r in runs:
        r.italic = False; r.font.size = Pt(9)
        r.bold = pos < cut
        pos += len(r.text)
for par in doc.paragraphs:
    if par.style.name in ('Image Caption', 'Table Caption'): bold_caption(par)
# highlight TBD placeholders
for par in doc.paragraphs:
    for r in par.runs:
        if 'TBD' in r.text: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
for tbl in doc.tables:
    for row in tbl.rows:
        for c in row.cells:
            for par in c.paragraphs:
                for r in par.runs:
                    if 'TBD' in r.text: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
# tables: width, no vertical lines, 9 pt single spaced
for tbl in doc.tables:
    tp = tbl._tbl.tblPr
    for tag in ('w:tblW', 'w:tblLayout', 'w:tblBorders'):
        for el in tp.findall(qn(tag)): tp.remove(el)
    w = OxmlElement('w:tblW'); w.set(qn('w:w'), '5000'); w.set(qn('w:type'), 'pct'); tp.append(w)
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'autofit'); tp.append(lay)
    bd = OxmlElement('w:tblBorders')
    for side, val in (('top', 'single'), ('left', 'nil'), ('bottom', 'single'), ('right', 'nil'), ('insideH', 'nil'), ('insideV', 'nil')):
        e = OxmlElement('w:' + side); e.set(qn('w:val'), val)
        if val == 'single': e.set(qn('w:sz'), '8'); e.set(qn('w:space'), '0'); e.set(qn('w:color'), '000000')
        bd.append(e)
    tp.append(bd)
    grid = tbl._tbl.find(qn('w:tblGrid')); ncol = len(tbl.columns); wts = []
    for ci in range(ncol):
        L = max((len(r.cells[ci].text) for r in tbl.rows if ci < len(r.cells)), default=1); wts.append(min(max(L, 6), 40))
    tot = sum(wts)
    for ci, g in enumerate(grid.findall(qn('w:gridCol'))): g.set(qn('w:w'), str(int(9000 * wts[ci] / tot)))
    for ri, r in enumerate(tbl.rows):
        for ci, c in enumerate(r.cells):
            tc = c._tc.get_or_add_tcPr()
            for el in tc.findall(qn('w:tcW')): tc.remove(el)
            cw = OxmlElement('w:tcW'); cw.set(qn('w:w'), str(int(5000 * wts[ci] / tot))); cw.set(qn('w:type'), 'pct'); tc.insert(0, cw)
            if ri == 0:
                b = OxmlElement('w:tcBorders'); e = OxmlElement('w:bottom'); e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '4'); e.set(qn('w:color'), '000000'); b.append(e); tc.append(b)
            for par in c.paragraphs:
                par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if ci > 1 else WD_ALIGN_PARAGRAPH.LEFT
                for run in par.runs: run.font.size = Pt(9); run.font.name = TNR; run.bold = (ri == 0) or None
# drop pandoc Title/Author/Date blocks (replaced by journal front matter)
for par in list(doc.paragraphs):
    if par.style.name in ('Title','Author','Date','Abstract'):
        par._element.getparent().remove(par._element)
# front matter
first = doc.paragraphs[0]
def front(text_runs, size, bold, align, space_after=6, spacing=WD_LINE_SPACING.SINGLE):
    p = first.insert_paragraph_before('')
    for txt, b in text_runs:
        r = p.add_run(txt); r.font.size = Pt(size); r.font.name = TNR; r.bold = b if b is not None else bold
    p.paragraph_format.alignment = align; p.paragraph_format.space_after = Pt(space_after); p.paragraph_format.line_spacing_rule = spacing
    return p
front([(TITLE, True)], 14, True, WD_ALIGN_PARAGRAPH.CENTER, 12)
front([('Abstract', True)], 10, True, WD_ALIGN_PARAGRAPH.LEFT, 3)
front([(l + x, None) for l, x in ABSTRACT], 9, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 8)
for p in doc.paragraphs[:3]:
    pass
front([('Keywords: ', True), (KEYWORDS, False)], 10, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 12)
# the abstract label runs of the structured abstract are non-bold per journal (9-pt, non-bold)
# page setup, line numbering, page numbers
for sec in doc.sections:
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.5); sec.top_margin = sec.bottom_margin = Cm(2.5)
    sp = sec._sectPr
    for el in sp.findall(qn('w:lnNumType')): sp.remove(el)
    ln = OxmlElement('w:lnNumType'); ln.set(qn('w:countBy'), '1'); ln.set(qn('w:restart'), 'continuous'); ln.set(qn('w:distance'), '360')
    # lnNumType must precede pgNumType/cols; insert after pgMar
    pgmar = sp.find(qn('w:pgMar')); pgmar.addnext(ln)
    sec.footer.is_linked_to_previous = False
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in list(fp.runs): r._r.getparent().remove(r._r)
    run = fp.add_run()
    for kind, txt in (('begin', None), ('instr', ' PAGE '), ('end', None)):
        if kind == 'instr':
            it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = txt; run._r.append(it)
        else:
            fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), kind); run._r.append(fc)
    run.font.name = TNR; run.font.size = Pt(10)
    ppr = fp._p.get_or_add_pPr(); sl = OxmlElement('w:suppressLineNumbers'); ppr.append(sl)
# suppress line numbers in tables / captions is not needed; headers/paragraph style tweaks done
doc.save(out)
print('saved', out)
