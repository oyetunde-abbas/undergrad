"""
"Tailor my resume for this job" — uses Google Gemini to
compare the person's resume against a specific job listing, modeled on the
classic recruiter-audit + XYZ-formula rewrite prompts (match score, missing
keywords, rewritten bullets).

Requires GEMINI_API_KEY in .env (see gemini_client.py).

The one rule that matters more here than in llm_fallback.py: this touches
someone's actual resume, which they might submit to real employers. A
model that invents accomplishments, numbers, or experience the person
never had would be actively harmful, not just unhelpful — it could get
someone caught lying to an employer. The prompt below is deliberately
strict about only rephrasing what's actually in the source resume, and
marking anything it can't verify as [FILL IN] rather than inventing a
plausible-sounding number, mirroring how a careful human resume coach
would flag a gap rather than quietly making something up.
"""

import logging

from gemini_client import generate_json, is_llm_available

logger = logging.getLogger("resume_tailor")

TAILOR_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "match_score": {"type": "INTEGER"},
        "missing_keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
        "strengths": {"type": "ARRAY", "items": {"type": "STRING"}},
        "tailored_bullets": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["match_score", "missing_keywords", "tailored_bullets"],
}

SYSTEM_PROMPT = """You are a careful, honest resume coach helping a candidate \
tailor their resume for one specific job. You are given the candidate's actual \
resume text and a job description.

Rules you must follow exactly:
1. NEVER invent an accomplishment, employer, job title, number, or skill that \
isn't genuinely present in the candidate's resume text. If a bullet would be \
stronger with a specific number the resume doesn't provide, write the bullet \
with the placeholder [FILL IN] instead of guessing a number.
2. Only rephrase and reorganize what's actually there. Your job is to surface \
and better express the candidate's real experience, not to embellish it.
3. missing_keywords: the skills/requirements the job asks for that do not \
appear anywhere in the resume — this helps the candidate know what to \
honestly address, not what to fake.
4. tailored_bullets: rewrite the candidate's existing experience bullets using \
the format "Accomplished [X] as measured by [Y] by doing [Z]" wherever the \
resume supports it — but only for real bullets from their actual resume, not \
invented ones.
5. match_score: 0-100, an honest estimate of how well the resume actually \
matches this specific job as written today, before any of your suggested edits.
6. strengths: 2-4 things already in the resume that map well to this job."""


def tailor_resume(resume_text, job_title, job_summary, job_skills, model=None):
    """
    Returns a dict with match_score / missing_keywords / strengths /
    tailored_bullets, or None if Gemini isn't configured or the response
    couldn't be parsed. Never raises.
    """
    if not resume_text or not resume_text.strip():
        logger.info("No resume text available — nothing to tailor")
        return None

    if not is_llm_available():
        logger.warning("GEMINI_API_KEY not set — can't tailor resume")
        return None

    job_description = f"Job title: {job_title}\n"
    if job_skills:
        job_description += f"Key skills required: {job_skills}\n"
    if job_summary:
        job_description += f"Description: {job_summary[:4000]}\n"

    prompt = (
        f"--- CANDIDATE'S RESUME ---\n{resume_text[:12000]}\n\n"
        f"--- JOB TO TAILOR FOR ---\n{job_description}"
    )

    parsed = generate_json(prompt, TAILOR_SCHEMA, system_instruction=SYSTEM_PROMPT)
    if not parsed:
        return None

    # Clamp match_score to a sane range in case the model returns something
    # out of bounds — models don't always respect numeric limits
    # a JSON schema alone can express.
    score = parsed.get("match_score", 0)
    try:
        score = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        score = 0

    return {
        "match_score": score,
        "missing_keywords": parsed.get("missing_keywords") or [],
        "strengths": parsed.get("strengths") or [],
        "tailored_bullets": parsed.get("tailored_bullets") or [],
    }
