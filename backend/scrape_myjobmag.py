"""
Phase 2 scraper for MyJobMag (myjobmag.com).

Same caveat as scrape_jobberman.py: this has NOT been run against the live
site from this sandbox (network-restricted). Built against real page
structure observed via a separate tool that could reach the site — real OG
meta tags, real "Posted"/"Deadline" dates, real labeled fields (Job Type,
Qualification, Experience, Location, Job Field), and real category-page
pagination (/jobs-by-field/{field}/2, /3, ...). Needs a first real run to
confirm selectors hold up; the field-extraction regex approach mirrors
scrape_jobberman.py's, which is the more failure-resistant part.

robots.txt was NOT checked for this domain — check myjobmag.com/robots.txt
before running this for real.

Categories covered (matching the user's chosen scope):
  - ICT / Computer
  - Engineering / Technical
  - Graduate Jobs
  - Internships
"""

import re
import logging
import time

import requests
from bs4 import BeautifulSoup

from db import insert_listing, touch_listings, close_listing_by_url
from tag_listings import infer_tags
from listing_summarizer import summarize_listing

logger = logging.getLogger("scrape_myjobmag")

BASE_URL = "https://www.myjobmag.com"

FIELD_SLUGS = {
    "ICT / Computer": "information-technology",
    "Engineering / Technical": "engineering",
    "Graduate Jobs": "graduate-jobs",
    "Internships": "internships-volunteering",
}

MAX_PAGES_PER_FIELD = 5

HEADERS = {
    "User-Agent": "UndergradJobAggregator/1.0 (personal project; respects robots.txt)"
}

REQUEST_DELAY_SECONDS = 1.5


def _field_page_url(slug, page):
    return f"{BASE_URL}/jobs-by-field/{slug}" if page == 1 else f"{BASE_URL}/jobs-by-field/{slug}/{page}"


def fetch_field_listing_urls(slug, max_pages=MAX_PAGES_PER_FIELD):
    """Returns a set of /job/{slug} listing URLs found across a field's paginated browse pages."""
    all_urls = set()
    for page in range(1, max_pages + 1):
        page_url = _field_page_url(slug, page)
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
            if re.match(r"^(https://www\.myjobmag\.com)?/job/[^/]+$", a["href"])
        }
        if not page_urls:
            break  # ran out of pages before max_pages
        all_urls |= page_urls
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_urls


def _extract_field(text, label):
    pattern = rf"{re.escape(label)}\s*:?\s*\n?\s*([^\n]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_listing_page(url, html):
    """Parses a single MyJobMag /job/ page into a dict matching our listings schema."""
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text("\n")

    if re.search(r"has expired", full_text, re.IGNORECASE):
        logger.info(f"Listing expired, skipping: {url}")
        close_listing_by_url(url)  # the source itself says it's over
        return None

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else None
    if not title:
        logger.warning(f"No title found, skipping: {url}")
        return None
    # title text is often "Role at Company" — split it for a cleaner title/company pair
    company = None
    at_split = re.split(r"\s+at\s+", title, maxsplit=1)
    if len(at_split) == 2:
        title, company = at_split[0].strip(), at_split[1].strip()

    if not company:
        page_title = soup.title.get_text() if soup.title else ""
        at_match = re.search(r"\bat\s+(.+?)\s*\|\s*MyJobMag", page_title, re.IGNORECASE)
        if at_match:
            company = at_match.group(1).strip()

    location = _extract_field(full_text, "Location")
    job_type = _extract_field(full_text, "Job Type")
    qualification = _extract_field(full_text, "Qualification")
    experience = _extract_field(full_text, "Experience")
    job_field = _extract_field(full_text, "Job Field")

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 40]
    raw_summary = max(paragraphs, key=len) if paragraphs else full_text[:500]

    remote = 1 if (location and "remote" in location.lower()) or (job_type and "remote" in job_type.lower()) else 0
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
        "deadline": None,
        "location": location or "Nigeria",
        "remote": remote,
        "work_style": tags.get("work_style"),
        "type": job_type or tags.get("type"),
        "category": tags.get("category"),
        "skills": tags.get("skills"),
        "experience_level": experience or tags.get("experience_level"),
        "source": "myjobmag",
        "content_hash": None,
        "status": "active",
        "needs_manual_review": 0,
    }
    return listing


def scrape_field(field_name, slug):
    inserted, failed = 0, 0
    urls = fetch_field_listing_urls(slug)
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
    for field_name, slug in FIELD_SLUGS.items():
        inserted, _failed = scrape_field(field_name, slug)
        total_inserted += inserted
    return total_inserted, 0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Starting MyJobMag scrape")
    run()
    logger.info("MyJobMag scrape complete")


if __name__ == "__main__":
    main()
