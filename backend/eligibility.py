"""
Nigerian-specific eligibility signals pulled out of listing text.

  nysc_req   'nysc_ok'   corps members / PPA placements welcome
             'post_nysc' NYSC discharge or exemption certificate required
             'siwes'     undergraduates / industrial-training (SIWES) placements
             None        text doesn't say
  min_degree 'first' | '2:1' | '2:2' | 'hnd' | 'ond' | None   (the stated MINIMUM)

None always means "unknown", never "no": filters treat unknown as possible, not
as excluded, so a missing phrase never hides a job from someone who could apply.
"""

import re

TIER = {"first": 5, "2:1": 4, "2:2": 3, "hnd": 2, "ond": 1}

_MIN_CUE = re.compile(
    r"\b(minimum|min\.?|at least|not less than|and above|or above|or higher|and higher|"
    r"required|requirement|must (have|hold|possess)|holders? of|with a|bsc|b\.?sc|bachelor)\b")
_CLASS_PATS = [
    ("first", re.compile(r"\b(first[- ]class|1st[- ]class)\b")),
    ("2:1", re.compile(r"(?<![\d:.])(2\s?[:.]\s?1)(?![\d:.])|\bsecond[- ]class upper\b|\bupper credit\b")),
    ("2:2", re.compile(r"(?<![\d:.])(2\s?[:.]\s?2)(?![\d:.])|\bsecond[- ]class lower\b|\blower credit\b")),
    ("hnd", re.compile(r"\bhnd\b|\bhigher national diploma\b")),
    ("ond", re.compile(r"\bond\b|\bordinary national diploma\b")),
]

_NYSC_OK = re.compile(
    r"(corps members?|corpers?|nysc (members|corps)|serving corps|ppa)[^.\n]{0,50}"
    r"(welcome|can apply|may apply|eligible|accepted|encouraged|open)"
    r"|open to[^.\n]{0,20}(corps members?|corpers?|nysc)|nysc (placement|ppa)|\bppa\b.{0,20}nysc")
_POST_NYSC = re.compile(
    r"(nysc|national youth service)[^.\n]{0,45}(discharge|exemption|completion)[^.\n]{0,15}certificate"
    r"|(completed|complete|finished|have done)[^.\n]{0,15}(nysc|national youth service)"
    r"|\bpost[- ]nysc\b|nysc (discharge|exemption)")
_SIWES = re.compile(r"\bsiwes\b|industrial training|\bi\.?t\.? (students?|placement)\b|undergraduates? (are )?(welcome|can apply|eligible)|penultimate year")


def nysc_requirement(text):
    t = " ".join((text or "").lower().split())
    if _NYSC_OK.search(t):
        return "nysc_ok"
    if _POST_NYSC.search(t):
        return "post_nysc"
    if _SIWES.search(t):
        return "siwes"
    return None


def min_degree(text):
    """Lowest class named in a sentence that states a requirement; None if unclear."""
    t = (text or "").lower()
    found = []
    for sentence in re.split(r"[.\n;•]+", t):
        if not _MIN_CUE.search(sentence):
            continue
        for tier, pat in _CLASS_PATS:
            if pat.search(sentence):
                found.append(tier)
    if not found:
        return None
    return min(found, key=lambda x: TIER[x])  # most lenient stated option


def analyse(title, summary):
    text = f"{title or ''}. {summary or ''}"
    return {"nysc_req": nysc_requirement(text), "min_degree": min_degree(text)}
