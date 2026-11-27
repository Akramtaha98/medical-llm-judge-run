#!/usr/bin/env python3
"""Set A claim segmentation: rule-based sentence splitting plus a review sheet for a second person.

Step 1  draft:     python code/segment_claims.py draft --answers data/setA/answers.jsonl --out data/claims
                   writes data/claims/segmentation_review.csv
Step 2  (human)    A second person checks every row and fills: ok (Y/N), corrected_text, note.
                   - corrected_text empty and ok=Y : claim_text is kept as drafted.
                   - to split a sentence into several atomic claims, write them in corrected_text separated by ' || '.
                   - to drop a courtesy / refusal / non-checkable sentence, write DROP in corrected_text.
                   - preserve negation, population, frequency, time and uncertainty; resolve a pronoun only if unambiguous.
Step 3  finalize:  python code/segment_claims.py finalize --review data/claims/segmentation_review.csv --out data/claims
                   writes data/claims/claims_A.csv  (claim_id, question_id, answer_id, set, source, split, generator,
                   original_span, char_start, char_end, claim_text, edit_type)

The draft only splits sentences and removes a lead-in such as "According to the passage,". It never rewrites content.
Rows with auto_flag set are the ones most likely to need a human edit.
"""
import argparse, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qkeys import qkey, assert_unique

ABBR = ["e.g.", "i.e.", "vs.", "Dr.", "Mr.", "Mrs.", "Ms.", "approx.", "etc.", "No.", "St.", "mg.", "Jr.", "Sr.", "U.S.", "cf."]
LEAD_INS = re.compile(
    r"^\s*(?:according to (?:the )?(?:passage|text|source|information provided)|based on (?:the )?(?:passage|text|source)|"
    r"(?:the )?(?:passage|text) (?:states|says|explains|notes|mentions|indicates)(?: that)?|from the passage)\s*[,:]?\s*", re.I)
REFUSAL = re.compile(r"(does not (?:answer|mention|provide|say|contain|include|specify)|doesn't (?:answer|mention|provide|say|contain|specify)|"
                     r"no information|not (?:mentioned|provided|specified) in the passage|cannot (?:answer|be answered)|"
                     r"i (?:hope|am sorry|cannot|can't)|please (?:consult|see|talk)|let me know|feel free)", re.I)
PRONOUN_START = re.compile(r"^(?:it|this|that|these|those|they|he|she|its|their|such)\b", re.I)


def split_sentences(text):
    """Return [(start, end, sentence)] using simple, auditable rules."""
    protected = text
    for i, a in enumerate(ABBR):
        protected = protected.replace(a, a.replace(".", "\u0001"))
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\u0001", protected)          # decimals
    protected = re.sub(r"\b([A-Z])\.(?=\s?[A-Z]\.)", "\\1\u0001", protected)  # initials
    cuts = [0]
    for m in re.finditer(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9\"'(\[*\-\u2022])|\n+\s*(?:[-*\u2022]|\d+[.)])\s+|\n{2,}", protected):
        cuts.append(m.end())
    cuts.append(len(text))
    out = []
    for a, b in zip(cuts, cuts[1:]):
        seg = text[a:b]
        lead = len(seg) - len(seg.lstrip(" \n\t-*\u2022"))
        s = seg.strip(" \n\t-*\u2022")
        if s:
            out.append((a + lead, a + lead + len(s), s))
    return out


def clean_claim(sentence):
    s = LEAD_INS.sub("", sentence).strip()
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def flags(sentence, claim):
    f = []
    if REFUSAL.search(sentence):
        f.append("possible_refusal_or_courtesy")
    if PRONOUN_START.match(claim):
        f.append("check_pronoun")
    if len(claim.split()) > 30 or claim.count(";") or re.search(r",\s*(?:and|or)\s", claim) or claim.count(",") >= 3:
        f.append("split_candidate")
    if len(claim.split()) < 4:
        f.append("very_short")
    return ";".join(f)


def draft(answers_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    rows = [json.loads(l) for l in open(answers_path, encoding="utf-8") if l.strip()]
    out = []
    assert_unique([qkey(r["source"], r["question_id"]) for r in rows], "(source, question_id) among answers")
    for r in sorted(rows, key=lambda r: (r["question_id"], r["source"])):
        qk = qkey(r["source"], r["question_id"])
        for n, (a, b, sent) in enumerate(split_sentences(r["answer"]), 1):
            claim = clean_claim(sent)
            out.append({"claim_id": f"A-{qk}-{n:02d}", "question_id": qk, "source": r["source"],
                        "split": r["split"], "generator": r["generator"], "char_start": a, "char_end": b,
                        "original_span": sent, "claim_text": claim, "auto_flag": flags(sent, claim),
                        "ok": "", "corrected_text": "", "note": ""})
    assert_unique([o["claim_id"] for o in out], "claim_id")
    path = os.path.join(outdir, "segmentation_review.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    nf = sum(1 for o in out if o["auto_flag"])
    print(f"{len(rows)} answers -> {len(out)} draft claims ({nf} flagged for attention) in {path}")


def finalize(review_path, outdir):
    rows = list(csv.DictReader(open(review_path, newline="", encoding="utf-8")))
    missing = [r["claim_id"] for r in rows if r["ok"].strip().upper() not in ("Y", "N")]
    if missing:
        sys.exit(f"{len(missing)} rows have no ok=Y/N (first: {missing[0]}). The second person must check every row.")
    out, dropped = [], 0
    for r in rows:
        ct = r["corrected_text"].strip()
        if ct.upper() == "DROP":
            dropped += 1; continue
        if r["ok"].strip().upper() == "N" and not ct:
            sys.exit(f"{r['claim_id']}: ok=N needs corrected_text or DROP")
        parts = [p.strip() for p in ct.split("||")] if ct else [r["claim_text"].strip()]
        for k, p in enumerate(parts):
            cid = r["claim_id"] if len(parts) == 1 else f"{r['claim_id']}{chr(97 + k)}"
            out.append({"claim_id": cid, "question_id": r["question_id"], "answer_id": r["question_id"], "set": "A",
                        "source": r["source"], "split": r["split"], "generator": r["generator"],
                        "original_span": r["original_span"], "char_start": r["char_start"], "char_end": r["char_end"],
                        "claim_text": p, "edit_type": ""})
    assert_unique([o["claim_id"] for o in out], "final Set A claim_id")
    path = os.path.join(outdir, "claims_A.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"{len(out)} final Set A claims ({dropped} sentences dropped) -> {path}")


def selftest():
    s = split_sentences("According to the passage, the risk is 2.5 times higher, e.g. in smokers. It may cause cough!\n- Rest helps\n- Fluids help")
    texts = [x[2] for x in s]
    assert len(texts) == 4, texts
    assert clean_claim(texts[0]).startswith("The risk is 2.5 times higher, e.g. in smokers"), clean_claim(texts[0])
    assert "check_pronoun" in flags(texts[1], clean_claim(texts[1]))
    assert "possible_refusal_or_courtesy" in flags("The passage does not mention dosage.", "The passage does not mention dosage.")
    import tempfile
    with tempfile.TemporaryDirectory() as td:  # same MedQuAD id in two collections must not collide
        p = os.path.join(td, "a.jsonl")
        with open(p, "w") as f:
            for src in ("NIDDK", "NHLBI"):
                f.write(json.dumps({"question_id": "0000095-1", "source": src, "split": "test", "generator": "g",
                                    "answer": "First sentence here. Second sentence here."}) + "\n")
        draft(p, td)
        ids = [r["claim_id"] for r in csv.DictReader(open(os.path.join(td, "segmentation_review.csv")))]
        assert len(ids) == len(set(ids)) == 4, ids
    print("segment_claims selftest passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draft", "finalize", "selftest"])
    ap.add_argument("--answers", default="data/setA/answers.jsonl"); ap.add_argument("--review")
    ap.add_argument("--out", default="data/claims")
    a = ap.parse_args()
    if a.cmd == "draft": draft(a.answers, a.out)
    elif a.cmd == "finalize": finalize(a.review or os.path.join(a.out, "segmentation_review.csv"), a.out)
    else: selftest()
