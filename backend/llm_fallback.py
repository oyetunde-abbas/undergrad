"""
LLM fallback extraction via Google Gemini, used when:
  (a) extract.py's deterministic chain found nothing usable at all, or
  (b) the person submitted raw pasted text with no URL (a WhatsApp forward,
      a tweet, a screenshot transcript) rather than a link to scrape.

Requires GEMINI_API_KEY in .env (see gemini_client.py). Returns None if
Gemini isn't configured or fails, so callers keep their existing fallback.
"""

import logging

from gemini_client import generate_json, is_llm_available

logger = logging.getLogger("llm_fallback")

JOB_POSTING_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_job_posting": {"type": "BOOLEAN"},
        "title": {"type": "STRING"},
        "company": {"type": "STRING"},
        "location": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "deadline": {"type": "STRING"},
        "employment_type": {"type": "STRING"},
        "remote": {"type": "BOOLEAN"},
    },
    "required": ["is_job_posting", "title"],
}

SYSTEM_PROMPT = """You extract structured job posting information from raw, \
possibly messy text (forwarded messages, tweets, screenshots, badly \
formatted web pages). If the text does not actually describe a job, \
internship, or similar opportunity, set is_job_posting to false and leave \
other fields empty. Only use information actually present in the text — \
never invent a company name, location, or deadline that isn't there. If a \
field isn't mentioned, leave it as an empty string rather than guessing. \
summary: 2-4 plain sentences covering only what the role involves, key \
requirements and pay if stated — no company marketing text."""


def is_ollama_available():
    """Kept for backwards compatibility — now reports whether Gemini is configured."""
    return is_llm_available()


def extract_with_llm(raw_text, model=None):
    """
    Sends raw text to Gemini and asks it to pull out job posting fields as
    structured JSON. Returns a dict on success, or None if Gemini isn't
    configured, errors, or decides the text isn't a job posting.
    `model` is ignored (set GEMINI_MODEL in .env instead); kept for compatibility.
    """
    if not raw_text or len(raw_text.strip()) < 20:
        logger.info("Text too short to bother sending to the LLM")
        return None

    if not is_llm_available():
        logger.warning("GEMINI_API_KEY not set — skipping LLM extraction")
        return None

    prompt = f"Text to analyze:\n\n{raw_text[:12000]}"
    parsed = generate_json(prompt, JOB_POSTING_SCHEMA, system_instruction=SYSTEM_PROMPT)
    if not parsed:
        return None

    if not parsed.get("is_job_posting") or not parsed.get("title"):
        logger.info("LLM decided this text isn't a job posting")
        return None

    return {
        "title": parsed.get("title"),
        "company": parsed.get("company") or None,
        "location": parsed.get("location") or None,
        "summary": parsed.get("summary") or raw_text[:2000],
        "deadline": parsed.get("deadline") or None,
        "employment_type": parsed.get("employment_type") or None,
        "remote": bool(parsed.get("remote")),
        "extraction_method": "llm",
    }
