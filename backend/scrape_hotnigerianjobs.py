"""
Phase 2 scraper for HotNigerianJobs (hotnigerianjobs.com).

Same caveat as the other Phase 2 scrapers: NOT run against the live site
from this sandbox. Built against real page structure observed via a
separate tool that could reach the site — real <h1> titles ("Role at
Company"), a real "Posted on {date} - hotnigerianjobs.com" pattern, real
labeled fields (Location:, Employment Type:, Application Closing Date),
and a real expired-listing phrase ("Sorry, this listing is no longer
open."). Needs a first real run to confirm selectors hold up.

robots.txt was NOT checked for this domain — check
hotnigerianjobs.com/robots.txt before running this for real.

Categories covered (field IDs found on a live listing page's sidebar):
  - 273: Computer / ICT / AI / Software / Hardware / Database / Data Analytics
  - 274: Engineering (general)
  - 231: Graduate Trainee / Fresh Graduate / Graduate Internship
  - 240: SIWES / Industrial Training / Undergraduate Internship
"""

import re
import logging
import time

import requests
from bs4 import BeautifulSoup

from db import insert_listing, touch_listings, close_listing_by_url
from tag_listings import infer_tags
from listing_summarizer import summarize_listing

logger = logging.getLogger("scrape_hotnigerianjobs")

BASE_URL = "https://www.hotnigerianjobs.com"

FIELD_IDS = {
    "Computer / ICT / AI": 273,
    "Engineering": 274,
    "Graduate Trainee / Internship": 231,
    "SIWES / Industrial Training": 240,
}

MAX_PAGES_PER_FIELD = 5
LISTING_URL_RE = re.compile(r"^(https://www\.hotnigerianjobs\.com)?/hotjobs/\d+/[^/]+\.html$")

HEADERS = {
    "User-Agent": "UndergradJobAggregator/1.0 (personal project; respects robots.txt)"
}

REQUEST_DELAY_SECONDS = 1.5


def _field_page_url(field_id, page):
    # HotNigerianJobs paginates as /field/{id}/{page}/ — page 1 is the bare /field/{id}/ URL
    return f"{BASE_URL}/field/{field_id}/" if page == 1 else f"{BASE_URL}/field/{field_id}/{page}/"


def fetch_field_listing_urls(field_id, max_pages=MAX_PAGES_PER_FIELD):
    all_urls = set()
    for page in range(1, max_pages + 1):
        page_url = _field_page_url(field_id, page)
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to load {page_url}: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        page_urls = {
            a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
            for a in soup.find_all("a", href=True)
            if LISTING_URL_RE.match(a["href"])
        }
        if not page_urls:
            break
        all_urls |= page_urls
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_urls


def _extract_field(text, label):
    pattern = rf"{re.escape(label)}\s*:?\s*\n?\s*([^\n]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_listing_page(url, html):
    """Parses a single HotNigerianJobs /hotjobs/ page into a dict matching our listings schema."""
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text("\n")

    if re.search(r"no longer open|listing has expired|no longer accepting applications", full_text, re.IGNORECASE):
        logger.info(f"Listing expired/closed, skipping: {url}")
        close_listing_by_url(url)  # the source itself says it's over
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else None
    if not title:
        logger.warning(f"No title found, skipping: {url}")
        return None

    company = None
    at_split = re.split(r"\s+at\s+", title, maxsplit=1)
    if len(at_split) == 2:
        title, company = at_split[0].strip(), at_split[1].strip()
        # strip a trailing "(Remote)"/"(N Positions)" style suffix from the role
        title = re.sub(r"\s*\(.*?\)\s*$", "", title).strip()

    location = _extract_field(full_text, "Location")
    employment_type = _extract_field(full_text, "Employment Type")
    closing_date = _extract_field(full_text, "Application Closing Date")

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 40]
    raw_summary = max(paragraphs, key=len) if paragraphs else full_text[:500]

    remote = 1 if location and "remote" in location.lower() else 0
    if not remote and re.search(r"\bremote\b", title, re.IGNORECASE):
        remote = 1

    tags = infer_tags(title, raw_summary, remote)

    summarized = summarize_listing(full_text, title)
    summary = summarized or raw_summary

    listing = {
        "title": title,
        "company": company,
        "summary": summary[:3000],
        "apply_url": url,
        "deadline": closing_date,
        "location": location or "Nigeria",
        "remote": remote,
        "work_style": tags.get("work_style"),
        "type": employment_type or tags.get("type"),
        "category": tags.get("category"),
        "skills": tags.get("skills"),
        "experience_level": tags.get("experience_level"),
        "source": "hotnigerianjobs",
        "content_hash": None,
        "status": "active",
        "needs_manual_review": 0,
    }
    return listing


def scrape_field(field_name, field_id):
    inserted, failed = 0, 0
    urls = fetch_field_listing_urls(field_id)
    logger.info(f"{field_name}: {len(urls)} listing URLs found")
    touch_listings(list(urls))  # seen this run, even if the page fails to parse below

    for url in urls:
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

    logger.info(f"{field_name}: inserted/updated={inserted}, failed={failed}")
    return inserted, failed


def run():
    """Entry point matching fetch_apis.py's (inserted, duplicates) return shape."""
    total_inserted = 0
    for field_name, field_id in FIELD_IDS.items():
        inserted, _failed = scrape_field(field_name, field_id)
        total_inserted += inserted
    return total_inserted, 0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Starting HotNigerianJobs scrape")
    run()
    logger.info("HotNigerianJobs scrape complete")


if __name__ == "__main__":
    main()
