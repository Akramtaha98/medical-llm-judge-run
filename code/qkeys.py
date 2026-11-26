"""Composite question key. MedQuAD question IDs are only unique within a collection (for example 0000095-1 exists in
both NIDDK and NHLBI), so every join in this project uses (source, question_id).

selected.csv keeps the raw MedQuAD question_id column unchanged (its hash is frozen). In every downstream file
(claims, worksheets, forms, gold, items) the column named question_id holds this composite key: SOURCE-qid.
"""


def qkey(source, question_id):
    return f"{source}-{question_id}"


def assert_unique(values, what):
    seen, dup = set(), []
    for v in values:
        if v in seen:
            dup.append(v)
        seen.add(v)
    if dup:
        raise SystemExit(f"duplicate {what}: {dup[:5]} ({len(dup)} duplicates)")
