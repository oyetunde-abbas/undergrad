"""
Rule-based scam screen for Nigerian job listings.

The classic pattern: a "job" that asks the applicant to pay for a form,
registration, training, medical test, uniform, etc. Real employers don't.

check(text) returns a short reason string if the text looks like a pay-to-apply
scam, else None. It is deliberately conservative — a false positive hides a real
job (admin can restore it), but a false negative lets a student get scammed, so
we err toward flagging, while ignoring clear negations ("no registration fee").
"""

import re

_FEE_TARGET = (
    r"(registration|application|processing|interview|screening|form|training|medical|"
    r"documentation|clearance|admin(istrative)?|verification|enrol+ment|uniform|starter kit|"
    r"id card|portal|access|software|assessment|test)"
)

_PATTERNS = [
    ("asks for a fee", re.compile(rf"\b{_FEE_TARGET}\s+(fee|fees|charge|charges|payment|deposit)\b")),
    ("asks you to pay", re.compile(
        r"\b(you|candidates?|applicants?)\b[^.\n]{0,30}\b(pay|paid|pays|deposit)\b[^.\n]{0,40}"
        r"\b(form|registration|training|medical|interview|processing|screening|uniform|kit|fee)")),
    ("asks you to pay", re.compile(
        r"\b(pay|send|transfer|deposit)\b\s+(a |an |the |your )?(small |one.?time |refundable |token )?"
        r"(fee|amount|sum|money)\b")),
    ("asks you to pay", re.compile(r"\bpay (for|to)\b[^.\n]{0,12}\b(the )?(form|registration|apply|application)\b")),
    ("asks you to buy a form", re.compile(r"\b(buy|purchase)\b\s+(the |an? )?(application |recruitment )?form\b")),
    ("refundable deposit", re.compile(r"\brefundable (deposit|fee|payment)\b")),
    ("asks for a transfer", re.compile(r"\b(send|transfer|pay)\b[^.\n]{0,25}(₦|\bn\s?\d[\d,]{2,}|\bngn\b)[^.\n]{0,30}\b(account|acct)\b")),
]

_NEGATION = re.compile(r"\b(no|not|never|without|free of|zero|don'?t|doesn'?t|do not|does not|free)\b")
_NEG_WINDOW = 35


def check(text):
    if not text:
        return None
    t = " ".join(str(text).lower().split())
    for reason, pat in _PATTERNS:
        for m in pat.finditer(t):
            before = t[max(0, m.start() - _NEG_WINDOW):m.end()]  # include the match: "you will NOT be asked to pay..."
            if _NEGATION.search(before):
                continue
            return f"{reason}: \"{m.group(0)[:60]}\""
    return None
