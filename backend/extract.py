"""
Generic deterministic extraction for arbitrary job-posting URLs, used by the
Phase 3 manual submission flow. Unlike the Phase 2 scrapers (which know each
site's exact structure ahead of time), this has to work reasonably well on
a URL it's never seen before.

Chain, in order of preference (each step only runs if the previous one
didn't get enough to work with):
  1. JSON-LD structured data (schema.org JobPosting) — most reliable when
     present, since the site is telling us exactly what the fields mean
  2. Open Graph / meta tags — less structured but very common
  3. trafilatura main-content extraction — strips nav/ads/footer clutter,
     leaves the actual article/posting text
  4. Basic regex/heuristic fallback on raw text — last resort

If none of these produce a confident result, the caller (routes/submit.py)
falls back to the LLM (llm_fallback.py) instead.
"""

import re
import logging

import extruct
import trafilatura
from bs4 import BeautifulSoup
from w3lib.html import get_base_url

logger = logging.getLogger("extract")

REQUIRED_FIELDS = {"title"}  # the bare minimum to consider extraction "successful"


def extract_from_jsonld(html, url):
    """Looks for schema.org JobPosting data in JSON-LD/microdata/RDFa."""
    try:
        base_url = get_base_url(html, url)
        data = extruct.extract(html, base_url=base_url, syntaxes=["json-ld", "microdata"])
    except Exception as e:
        logger.warning(f"extruct failed on {url}: {e}")
        return None

    candidates = data.get("json-ld", []) + [
        item.get("properties", {}) | {"@type": item.get("type")}
        for item in data.get("microdata", [])
    ]

    for item in candidates:
        item_type = item.get("@type", "")
        type_str = item_type if isinstance(item_type, str) else " ".join(item_type or [])
        if "JobPosting" not in type_str:
            continue

        title = item.get("title")
        if not title:
            continue

        org = item.get("hiringOrganization", {})
        company = org.get("name") if isinstance(org, dict) else org

        loc = item.get("jobLocation", {})
        if isinstance(loc, list):
            loc = loc[0] if loc else {}
        address = loc.get("address", {}) if isinstance(loc, dict) else {}
        location = None
        if isinstance(address, dict):
            location = ", ".join(
                filter(None, [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")])
            ) or None

        return {
            "title": title,
            "company": company,
            "location": location,
            "summary": item.get("description"),
            "deadline": item.get("validThrough"),
            "employment_type": item.get("employmentType"),
            "extraction_method": "json-ld",
        }

    return None


def extract_from_meta_tags(html, url):
    """Falls back to Open Graph tags specifically — much more common than JSON-LD.
    Deliberately does NOT fall back to the generic <title> tag: a page title
    like "Home | SomeSite" isn't a reliable job title, and treating it as a
    success would stop the chain before trafilatura gets a chance to do
    better full-content extraction."""
    soup = BeautifulSoup(html, "lxml")

    def meta(prop_or_name):
        tag = soup.find("meta", property=prop_or_name) or soup.find("meta", attrs={"name": prop_or_name})
        return tag.get("content", "").strip() if tag else None

    title = meta("og:title")
    if not title:
        return None

    description = meta("og:description") or meta("description")

    return {
        "title": title,
        "company": None,
        "location": None,
        "summary": description,
        "deadline": None,
        "employment_type": None,
        "extraction_method": "meta-tags",
    }


def extract_from_trafilatura(html, url):
    """
    Last structured-ish attempt: pull clean main-content text via trafilatura
    (it strips nav/ads/footer clutter well), but get the title from the
    actual <h1> tag rather than guessing from the extracted text — trafilatura
    doesn't reliably put a newline between a heading and the paragraph that
    follows it, so "take the first line" is not a safe way to find a title.
    """
    extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
    if not extracted or len(extracted) < 50:
        return None

    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None
    if title and len(title) > 200:
        title = None
    if not title:
        # last resort: first sentence-ish chunk, capped to a sane length
        first_chunk = extracted.split(".")[0].strip()
        title = first_chunk[:120] if 10 < len(first_chunk) <= 120 else None
    if not title:
        return None

    return {
        "title": title,
        "company": None,
        "location": None,
        "summary": extracted[:3000],
        "deadline": None,
        "employment_type": None,
        "extraction_method": "trafilatura",
        "raw_text": extracted,  # kept around in case the LLM fallback needs the full text
    }


def extract_job_posting(html, url):
    """
    Runs the full deterministic chain. Returns a dict on success (has at
    least a usable title), or None if nothing in the chain produced enough
    to work with — signaling the caller to try the LLM fallback instead.
    """
    for extractor in (extract_from_jsonld, extract_from_meta_tags, extract_from_trafilatura):
        try:
            result = extractor(html, url)
        except Exception as e:
            logger.warning(f"{extractor.__name__} raised on {url}: {e}")
            continue

        if result and result.get("title"):
            logger.info(f"Extracted via {result['extraction_method']}: {result['title'][:60]}")
            return result

    logger.info(f"Deterministic extraction found nothing usable for {url}")
    return None
