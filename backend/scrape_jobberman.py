"""
Phase 2 scraper for Jobberman (jobberman.com).

IMPORTANT — this module has NOT been run against the live site. The
development sandbox this was built in cannot reach jobberman.com over the
network (only a small allowlist of domains is reachable from there), so
every real HTTP request in this file is untested. What *has* been verified,
using Jobberman's real sitemap XML and listing-page content pulled through a
separate tool that could reach the site:

  - The sitemap structure and URLs below (sitemap-listings-index-en.xml and
    the per-category sitemaps) are real and were fetched directly.
  - robots.txt was checked and explicitly allows /listings/ and /jobs/ paths
    (only query-string filters and pagination beyond page 10 are disallowed).
  - Listing pages expose consistent labeled fields as visible text: "Min
    Qualification", "Experience Level", "Experience Length", "Language
    Requirement", "Working Hours", "Applicant Location" — the regex-based
    extraction below is built around that real, observed structure.

What's NOT verified: the exact HTML tag/class structure (id, class names)
since the tool used to inspect the site returns extracted/converted content,
not raw HTML. So the BeautifulSoup selectors below are a best-effort first
pass and may need small adjustments once run for real. Run this file
directly (`python3 scrape_jobberman.py`) on a machine with normal internet
access and check the output before wiring it into a scheduled job.

Categories covered (per user's chosen scope — tech roles + internship/
graduate roles across all fields):
  - Software & Data (sitemap)
  - Engineering & Technology (sitemap)
  - Internship & Graduate, all fields (category browse pages, paginated)
"""

import re
import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from db import (
    insert_listing, get_site_hash, set_site_hash,
    touch_listings, begin_scrape, finish_scrape,
)
from tag_listings import infer_tags
from listing_summarizer import summarize_listing

logger = logging.getLogger("scrape_jobberman")

BASE_URL = "https://www.jobberman.com"

SITEMAP_URLS = {
    "Software & Data": f"{BASE_URL}/sitemap-listings-software-data-en.xml",
    "Engineering & Technology": f"{BASE_URL}/sitemap-listings-engineering-technology-en.xml",
}

# robots.txt explicitly allows page=2 through page=10 for this path
INTERNSHIP_GRADUATE_PAGES = [f"{BASE_URL}/jobs/internship-graduate"] + [
    f"{BASE_URL}/jobs/internship-graduate?page={n}" for n in range(2, 11)
]

HEADERS = {
    # Identify honestly as a script, not a masquerading browser — this is a
    # personal aggregator pulling a small, infrequent volume of pages, not
    # bulk harvesting, and robots.txt already grants access to these paths.
    "User-Agent": "UndergradJobAggregator/1.0 (personal project; respects robots.txt)"
}

REQUEST_DELAY_SECONDS = 1.5  # be a polite, low-volume visitor


def fetch_sitemap_listing_urls(sitemap_url):
    """Returns a list of (url, lastmod) tuples from a Jobberman category sitemap."""
    resp = requests.get(sitemap_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "xml")
    results = []
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        lastmod = url_tag.find("lastmod")
        if loc:
            results.append((loc.text.strip(), lastmod.text.strip() if lastmod else None))
    return results


def _extract_field(text, label):
    """Pulls 'Value' out of a 'Label: Value' or 'Label\\nValue' pattern in extracted page text."""
    pattern = rf"{re.escape(label)}\s*:?\s*\n?\s*([^\n]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_listing_page(url, html):
    """
    Parses a single Jobberman /listings/ page into a dict matching our
    listings table schema. Returns None if the page doesn't look like a
    real listing (e.g. expired/removed).
    """
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text("\n")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else None
    if not title:
        logger.warning(f"No title found, skipping: {url}")
        return None

    # Company name commonly appears near the title as a link or bold text;
    # fall back to the page <title> tag pattern "Role at Company | Jobberman"
    company = None
    page_title = soup.title.get_text() if soup.title else ""
    at_match = re.search(r"\bat\s+(.+?)\s*\|\s*Jobberman", page_title, re.IGNORECASE)
    if at_match:
        company = at_match.group(1).strip()

    location = _extract_field(full_text, "Applicant Location") or _extract_field(full_text, "Location")
    qualification = _extract_field(full_text, "Min Qualification")
    experience_level_raw = _extract_field(full_text, "Experience Level")
    experience_length = _extract_field(full_text, "Experience Length")
    working_hours = _extract_field(full_text, "Working Hours")

    # Fallback description: longest paragraph block, since Jobberman doesn't
    # mark up a single clean "description" div in what we could inspect.
    # This often grabs generic company boilerplate rather than the actual
    # role details — used as a fallback and as input for tag inference, but
    # replaced with a real summary below when Gemini's available.
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 40]
    raw_summary = max(paragraphs, key=len) if paragraphs else full_text[:500]

    remote = 1 if location and "remote" in location.lower() else 0
    if not remote and re.search(r"\bremote\b", title, re.IGNORECASE):
        remote = 1

    tags = infer_tags(title, raw_summary, remote)

    # Try for a real essentials-only summary (pay, requirements, what you
    # need to know before applying) instead of the raw paragraph grab.
    # Falls back to the raw paragraph if Gemini isn't available — never
    # blocks scraping on this.
    summarized = summarize_listing(full_text, title)
    summary = summarized or raw_summary

    listing = {
        "title": title,
        "company": company,
        "summary": summary[:3000],
        "apply_url": url,
        "deadline": None,
        "location": location or "Nigeria",
        "remote": remote,
        "work_style": tags.get("work_style"),
        "type": tags.get("type"),
        "category": tags.get("category"),
        "skills": tags.get("skills"),
        "experience_level": experience_level_raw or tags.get("experience_level"),
        "source": "jobberman",
        "content_hash": None,
        "status": "active",
        "needs_manual_review": 0,
    }
    return listing


def scrape_sitemap_category(category_name, sitemap_url, max_listings=None):
    """Scrapes one sitemap-backed category, skipping listings whose lastmod hasn't changed."""
    inserted, skipped_unchanged, failed = 0, 0, 0

    urls = fetch_sitemap_listing_urls(sitemap_url)
    logger.info(f"{category_name}: {len(urls)} URLs in sitemap")

    # Every URL in the sitemap is "seen" this run, even the ones we skip as
    # unchanged below — otherwise unchanged listings would look like they vanished.
    touch_listings([u for u, _lastmod in urls])

    if max_listings:
        urls = urls[:max_listings]

    for url, lastmod in urls:
        known_hash = get_site_hash(url)
        if lastmod and known_hash == lastmod:
            skipped_unchanged += 1
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            listing = parse_listing_page(url, resp.text)
            if listing:
                insert_listing(listing)
                set_site_hash(url, lastmod or datetime.now(timezone.utc).isoformat())
                inserted += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to process {url}: {e}")

        time.sleep(REQUEST_DELAY_SECONDS)

    logger.info(
        f"{category_name}: inserted/updated={inserted}, unchanged-skipped={skipped_unchanged}, failed={failed}"
    )
    return inserted, skipped_unchanged, failed


def scrape_internship_graduate_pages(max_pages=None):
    """
    Scrapes the Internship & Graduate category browse pages (all fields).
    No sitemap/lastmod available here, so this always re-checks each listing
    URL it finds — content_hash change detection still prevents needless
    DB writes via insert_listing's own UPSERT-on-apply_url behavior.
    """
    inserted, failed = 0, 0
    index_failed = 0  # category index pages we could not load (these hide listings from us)
    pages = INTERNSHIP_GRADUATE_PAGES[:max_pages] if max_pages else INTERNSHIP_GRADUATE_PAGES

    for page_url in pages:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            listing_links = {
                a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
                for a in soup.find_all("a", href=True)
                if "/listings/" in a["href"]
            }
        except Exception as e:
            logger.error(f"Failed to load category page {page_url}: {e}")
            failed += 1
            index_failed += 1
            continue

        if not listing_links:
            # ran out of results before hitting max_pages — stop early
            break

        touch_listings(list(listing_links))
        for url in listing_links:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                listing = parse_listing_page(url, resp.text)
                if listing:
                    insert_listing(listing)
                    inserted += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to process {url}: {e}")
            time.sleep(REQUEST_DELAY_SECONDS)

    logger.info(f"Internship & Graduate: inserted/updated={inserted}, failed={failed}")
    return inserted, failed, index_failed


def run():
    """
    Entry point matching the (inserted, duplicates) return shape used by
    fetch_apis.py's other sources, so this can be dropped into the same
    sources list and benefit from its shared logging/crash-isolation.
    """
    total_inserted = 0
    total_unchanged = 0
    scrape = begin_scrape("jobberman")

    # A sitemap fetch failure raises and aborts the run before finish_scrape,
    # so nothing gets marked missing off a half-finished scrape.
    for category_name, sitemap_url in SITEMAP_URLS.items():
        inserted, unchanged, _failed = scrape_sitemap_category(category_name, sitemap_url)
        total_inserted += inserted
        total_unchanged += unchanged

    grad_inserted, _grad_failed, grad_index_failed = scrape_internship_graduate_pages()
    total_inserted += grad_inserted

    # Jobberman is the one source whose index we cover in full (sitemaps + category
    # pages), so it's the one we trust to say "this listing is gone".
    summary = finish_scrape(scrape, complete=(grad_index_failed == 0))
    logger.info(f"Jobberman lifecycle: {summary}")

    return total_inserted, total_unchanged


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Starting Jobberman scrape")
    run()
    logger.info("Jobberman scrape complete")


if __name__ == "__main__":
    main()
