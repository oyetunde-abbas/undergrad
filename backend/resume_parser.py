"""
Extracts plain text from an uploaded resume (PDF or DOCX), then matches it
against the same SKILL_KEYWORDS vocabulary used to tag job listings — so a
resume and a job posting get scored against identical skill definitions,
which is what makes a match score meaningful.

.doc (old binary Word format, not .docx) is accepted for upload but NOT
parsed here — there's no lightweight pure-Python reader for the legacy
binary format, and pulling in a heavier dependency (e.g. antiword, or a
LibreOffice conversion step) isn't worth it for how rare .doc uploads are
likely to be in practice. Skill extraction is simply skipped for .doc
files; the file itself still uploads and stores fine.
"""

import io
import re
import logging

from pypdf import PdfReader
from docx import Document

from tag_listings import SKILL_KEYWORDS

logger = logging.getLogger("resume_parser")


def extract_text(file_bytes, extension):
    extension = extension.lower()
    try:
        if extension == ".pdf":
            return _extract_pdf_text(file_bytes)
        elif extension == ".docx":
            return _extract_docx_text(file_bytes)
        elif extension == ".doc":
            logger.info("Skill extraction skipped for legacy .doc format")
            return ""
    except Exception as e:
        logger.warning(f"Failed to extract text from resume ({extension}): {e}")
        return ""
    return ""


def _extract_pdf_text(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def _extract_docx_text(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def extract_skills(resume_text):
    """
    Matches SKILL_KEYWORDS against resume text as whole words/phrases
    (case-insensitive), same approach as job-listing tagging. Returns the
    list of skills actually found, in the same casing as SKILL_KEYWORDS
    (e.g. "React", not "react") so they display consistently with skills
    added any other way.
    """
    if not resume_text or not resume_text.strip():
        return []

    found = []
    for skill in SKILL_KEYWORDS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, resume_text, re.IGNORECASE):
            found.append(skill)
    return found


def parse_resume(file_bytes, extension):
    """Convenience wrapper: extract text, then extract skills from it."""
    text = extract_text(file_bytes, extension)
    skills = extract_skills(text)
    return {"text_extracted": bool(text.strip()), "skills": skills, "text": text}
