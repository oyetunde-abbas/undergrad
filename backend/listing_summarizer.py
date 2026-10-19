"""
Summarizes a scraped job listing down to only what a student needs to decide
whether to apply — role, pay, job type, arrangement, location, deadline, NYSC
status, qualification, requirements, duties, skills, how to apply and scam
warnings — instead of grabbing the first/longest paragraph (usually company
"who we are" boilerplate).

Used by the scraped sources (Jobberman, MyJobMag, HotNigerianJobs).

Uses Gemini (see gemini_client.py). If Gemini isn't configured or fails,
falls back to extract_key_sections(), which keeps only the text under useful
headings ("Requirements", "Responsibilities", "Salary", "Deadline", ...).
Never blocks scraping.

Public API unchanged: summarize_listing(raw_text, title) -> str | None
"""

import logging
import re

from gemini_client import generate_json, is_llm_available

logger = logging.getLogger("listing_summarizer")

MAX_INPUT_CHARS = 12000

SUMMARY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "role_summary": {"type": "STRING"},
        "pay": {"type": "STRING"},
        "employment_type": {"type": "STRING"},
        "work_arrangement": {"type": "STRING"},
        "location": {"type": "STRING"},
        "deadline": {"type": "STRING"},
        "nysc": {"type": "STRING"},
        "qualification": {"type": "STRING"},
        "experience": {"type": "STRING"},
        "requirements": {"type": "ARRAY", "items": {"type": "STRING"}},
        "responsibilities": {"type": "ARRAY", "items": {"type": "STRING"}},
        "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
        "how_to_apply": {"type": "STRING"},
        "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["role_summary"],
}

SYSTEM_PROMPT = """You turn a scraped Nigerian job posting into a short fact \
sheet for university students and recent graduates. Use ONLY information \
actually present in the text — never invent pay, deadlines or requirements. \
Leave a field as an empty string / empty list if it isn't stated.

role_summary: 1-2 plain sentences on what the job actually involves.
pay: salary or stipend exactly as stated.
employment_type: e.g. Full-time, Internship, Contract, Graduate trainee.
work_arrangement: Remote, Hybrid or On-site.
location: city/state.
deadline: application closing date as written.
nysc: e.g. "Corps members accepted", "NYSC certificate required".
qualification: degree, grade (e.g. 2:1) or discipline required.
experience: years of experience required.
requirements: up to 6 short phrases.
responsibilities: up to 5 short phrases.
skills: up to 8 skill keywords.
how_to_apply: email/link/method in one line.
warnings: scam red flags only, e.g. asks for payment to apply, personal \
Gmail-only contact for a big company, unrealistic pay.

Ignore company marketing, benefits fluff, equal-opportunity statements, \
navigation text and other listings on the page. Short and accurate beats long."""

KEY_HEADINGS = re.compile(
    r"^\s*(job\s+)?(summary|description|overview|role|responsibilit\w*|duties|"
    r"what you.?ll do|requirements?|qualifications?|skills|experience|"
    r"salary|pay|remuneration|compensation|benefits|location|deadline|"
    r"closing date|method of application|how to apply|application)\b",
    re.IGNORECASE,
)
SKIP_HEADINGS = re.compile(
    r"^\s*(about (us|the company)|who we are|our (company|mission|values)|"
    r"company (profile|overview)|equal opportunity|disclaimer|share|related jobs)\b",
    re.IGNORECASE,
)


def _clean(items, limit):
    out = []
    for item in items or []:
        item = (item or "").strip()
        if item and item not in out:
            out.append(item)
    return out[:limit]


def format_summary(parsed):
    """Turns the structured fields into one clean block of text for the
    listing's summary column."""
    lines = []
    role = (parsed.get("role_summary") or "").strip()
    if role:
        lines.append(role)

    facts = []
    for label, key in [
        ("Pay", "pay"),
        ("Type", "employment_type"),
        ("Work", "work_arrangement"),
        ("Location", "location"),
        ("Deadline", "deadline"),
        ("NYSC", "nysc"),
        ("Qualification", "qualification"),
        ("Experience", "experience"),
    ]:
        value = (parsed.get(key) or "").strip()
        if value:
            facts.append(f"{label}: {value}")
    if facts:
        lines.append("\n".join(facts))

    for label, key, limit in [
        ("Requirements", "requirements", 6),
        ("Responsibilities", "responsibilities", 5),
    ]:
        items = _clean(parsed.get(key), limit)
        if items:
            lines.append(f"{label}:\n" + "\n".join(f"- {i}" for i in items))

    skills = _clean(parsed.get("skills"), 8)
    if skills:
        lines.append("Skills: " + ", ".join(skills))

    how = (parsed.get("how_to_apply") or "").strip()
    if how:
        lines.append(f"How to apply: {how}")

    warnings = _clean(parsed.get("warnings"), 4)
    if warnings:
        lines.append("Caution: " + "; ".join(warnings) + ". Never pay to apply for a job.")

    return "\n\n".join(lines)


def extract_key_sections(raw_text, max_chars=1800):
    """No-AI fallback: keep only text under useful headings, skipping
    company boilerplate. Returns None if no useful headings were found."""
    if not raw_text:
        return None
    kept, keeping = [], False
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_heading = len(stripped) < 60
        if is_heading and SKIP_HEADINGS.match(stripped):
            keeping = False
            continue
        if is_heading and KEY_HEADINGS.match(stripped):
            keeping = True
            kept.append("\n" + stripped.rstrip(":") + ":")
            continue
        if keeping:
            kept.append(stripped)
    text = "\n".join(kept).strip()
    if len(text) < 80:
        return None
    return text[:max_chars].rsplit("\n", 1)[0] if len(text) > max_chars else text


def summarize_listing_structured(raw_text, title):
    """Returns the structured dict from Gemini, or None."""
    if not raw_text or not raw_text.strip() or not is_llm_available():
        return None
    prompt = f"Job title: {title}\n\nRaw scraped listing text:\n{raw_text[:MAX_INPUT_CHARS]}"
    return generate_json(prompt, SUMMARY_SCHEMA, system_instruction=SYSTEM_PROMPT)


def summarize_listing(raw_text, title, model=None):
    """
    Returns a clean, essentials-only summary string, or None — callers then
    fall back to their existing raw-text extraction. `model` is ignored
    (set GEMINI_MODEL in .env); kept for compatibility.
    """
    if not raw_text or not raw_text.strip():
        return None

    parsed = summarize_listing_structured(raw_text, title)
    if parsed:
        formatted = format_summary(parsed)
        if formatted.strip():
            return formatted
        logger.warning(f"Gemini returned an empty summary for '{title}'")
    else:
        logger.info(f"No AI summary for '{title}' — using heading-based extraction")

    return extract_key_sections(raw_text)
