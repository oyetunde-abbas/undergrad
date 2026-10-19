import re
import requests
import os
import logging
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv
from db import insert_listing, expire_listings
from tag_listings import infer_tags
from scrape_jobberman import run as run_jobberman
from scrape_myjobmag import run as run_myjobmag
from scrape_hotnigerianjobs import run as run_hotnigerianjobs

load_dotenv()

LOG_PATH = Path(__file__).resolve().parent / "fetch_apis.log"

logger = logging.getLogger("fetch_apis")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


URL = "https://www.arbeitnow.com/api/job-board-api"
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"
REMOTEOK_URL = "https://remoteok.com/api"


KEYWORDS = [
    "software",
    "developer",
    "engineer",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "python",
    "java",
    "javascript",
    "react",
    "node",
    "data",
    "machine learning",
    "artificial intelligence",
    "ai",
    "graduate",
    "graduate trainee",
    "entry level",
    "entry-level",
    "junior",
    "intern",
    "internship"
]


# ===========================
# Helper Functions
# ===========================

def clean_description(text):

    if not text:
        return ""

    # Preserve structure before stripping tags: turn list items and paragraph/line
    # breaks into real newlines so the result reads like a formatted job posting
    # instead of one flattened run-on blob.
    text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<(p|br|div|/p|/div)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<(ul|ol|/ul|/ol)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Strip any remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Collapse repeated spaces/tabs WITHIN a line, but keep the newlines we just added
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Unescape common HTML entities that survive tag-stripping
    text = text.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"')

    return text.strip()



def is_relevant_job(title, description):

    search_text = f"{title} {description}".lower()

    return any(
        keyword in search_text
        for keyword in KEYWORDS
    )



# ===========================
# Arbeitnow API
# ===========================

def fetch_arbeitnow():

    response = requests.get(URL, timeout=30)

    if response.status_code != 200:
        return 0, 0

    jobs = response.json().get("data", [])

    inserted = 0
    duplicates = 0


    for job in jobs:

        title = job.get("title", "")

        description = clean_description(
            job.get("description")
        )


        if not is_relevant_job(title, description):
            continue


        listing = {

            "title": title,
            "company": job.get("company_name"),
            "summary": description[:3000],
            "apply_url": job.get("url"),
            "location": job.get("location"),
            "remote": 1 if "remote" in description.lower() else 0,
            "nysc_free": 0,
            "eligibility_notes": "",
            "source": "arbeitnow"

        }
        listing.update(infer_tags(title, description, listing["remote"]))


        if insert_listing(listing):
            inserted += 1
        else:
            duplicates += 1


    return inserted, duplicates





# ===========================
# Jobicy API
# ===========================

def fetch_jobicy():

    response = requests.get(
        JOBICY_URL,
        timeout=30
    )


    if response.status_code != 200:
        return 0, 0


    jobs = response.json().get(
        "jobs",
        []
    )


    inserted = 0
    duplicates = 0


    for job in jobs:


        title = job.get(
            "jobTitle",
            ""
        )


        description = clean_description(
            job.get("jobExcerpt")
        )


        if not is_relevant_job(
            title,
            description
        ):
            continue



        listing = {

            "title": title,
            "company": job.get("companyName"),
            "summary": description[:3000],
            "apply_url": job.get("url"),
            "location": job.get("jobGeo"),
            "remote": 1,
            "nysc_free": 0,
            "eligibility_notes": "",
            "source": "jobicy"

        }
        listing.update(infer_tags(title, description, listing["remote"]))


        if insert_listing(listing):
            inserted += 1
        else:
            duplicates += 1


    return inserted, duplicates





# ===========================
# RemoteOK API
# ===========================

def fetch_remoteok():


    headers = {
        "User-Agent": "Mozilla/5.0"
    }


    response = requests.get(
        REMOTEOK_URL,
        headers=headers,
        timeout=30
    )


    if response.status_code != 200:
        return 0, 0


    jobs = response.json()[1:]


    inserted = 0
    duplicates = 0



    for job in jobs:


        title = job.get(
            "position",
            ""
        )


        description = clean_description(
            job.get("description")
        )


        if not is_relevant_job(
            title,
            description
        ):
            continue



        listing = {

            "title": title,
            "company": job.get("company"),
            "summary": description[:3000],
            "apply_url": job.get("apply_url"),
            "location": job.get("location"),
            "remote": 1,
            "nysc_free": 0,
            "eligibility_notes": "",
            "source": "remoteok"

        }
        listing.update(infer_tags(title, description, listing["remote"]))


        if insert_listing(listing):
            inserted += 1
        else:
            duplicates += 1



    return inserted, duplicates





# ===========================
# Adzuna API
# ===========================

def fetch_adzuna():


    app_id = os.getenv(
        "ADZUNA_APP_ID"
    )

    app_key = os.getenv(
        "ADZUNA_APP_KEY"
    )


    if not app_id or not app_key:

        return 0, 0



    url = (

        "https://api.adzuna.com/v1/api/jobs/us/search/1"

        f"?app_id={app_id}"

        f"&app_key={app_key}"

        "&results_per_page=50"

        "&what=software%20developer"

    )


    response = requests.get(
        url,
        timeout=30
    )


    if response.status_code != 200:

        return 0, 0



    data = response.json()



    inserted = 0
    duplicates = 0



    for job in data.get(
        "results",
        []
    ):



        title = job.get(
            "title",
            ""
        )


        description = clean_description(
            job.get("description")
        )



        if not is_relevant_job(
            title,
            description
        ):
            continue



        listing = {


            "title": title,

            "company": job.get(
                "company",
                {}
            ).get(
                "display_name"
            ),


            "summary": description[:3000],


            "apply_url": job.get(
                "redirect_url"
            ),


            "location": job.get(
                "location",
                {}
            ).get(
                "display_name"
            ),


            "remote": 1 if "remote" in (
                f"{title} {description}"
            ).lower() else 0,


            "nysc_free": 0,

            "eligibility_notes": "",

            "source": "adzuna"

        }
        listing.update(infer_tags(title, description, listing["remote"]))



        if insert_listing(listing):

            inserted += 1

        else:

            duplicates += 1



    return inserted, duplicates





# ===========================
# Main Program
# ===========================

def main():

    total_inserted = 0
    total_duplicates = 0
    failures = []

    sources = [
        ("Arbeitnow", fetch_arbeitnow),
        ("Jobicy", fetch_jobicy),
        ("RemoteOK", fetch_remoteok),
        ("Adzuna", fetch_adzuna),
        ("Jobberman", run_jobberman),
        ("MyJobMag", run_myjobmag),
        ("HotNigerianJobs", run_hotnigerianjobs),
    ]

    logger.info("=" * 30)
    logger.info("Starting fetch run")
    logger.info("=" * 30)

    for name, function in sources:
        try:
            inserted, duplicates = function()
        except Exception as e:
            failures.append(name)
            logger.error(f"{name} FAILED: {e}")
            logger.error(traceback.format_exc())
            continue

        logger.info(f"{name}: inserted={inserted}, duplicates(refreshed)={duplicates}")
        total_inserted += inserted
        total_duplicates += duplicates

    logger.info("-" * 30)
    logger.info(f"TOTAL: inserted={total_inserted}, duplicates(refreshed)={total_duplicates}")
    if failures:
        logger.warning(f"Sources that failed this run: {', '.join(failures)}")
    try:
        logger.info(f"Expiry sweep: {expire_listings()} listings marked expired")
    except Exception as e:
        logger.error(f"Expiry sweep failed: {e}")
    logger.info("Fetch run complete.")
    logger.info("=" * 30 + "\n")


if __name__ == "__main__":

    main()