import re
import requests
import os
from dotenv import load_dotenv
from db import insert_listing

load_dotenv()


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

    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)

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
            "summary": description[:500],
            "apply_url": job.get("url"),
            "location": job.get("location"),
            "remote": 1 if "remote" in description.lower() else 0,
            "nysc_free": 0,
            "eligibility_notes": "",
            "source": "arbeitnow"

        }


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
            "summary": description[:500],
            "apply_url": job.get("url"),
            "location": job.get("jobGeo"),
            "remote": 1,
            "nysc_free": 0,
            "eligibility_notes": "",
            "source": "jobicy"

        }


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
            "summary": description[:500],
            "apply_url": job.get("apply_url"),
            "location": job.get("location"),
            "remote": 1,
            "nysc_free": 0,
            "eligibility_notes": "",
            "source": "remoteok"

        }


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


            "summary": description[:500],


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



    sources = [

        ("Arbeitnow", fetch_arbeitnow),

        ("Jobicy", fetch_jobicy),

        ("RemoteOK", fetch_remoteok),

        ("Adzuna", fetch_adzuna)

    ]



    for name, function in sources:


        inserted, duplicates = function()


        print("\n" + name)

        print(
            f"  Inserted : {inserted}"
        )

        print(
            f"  Duplicates : {duplicates}"
        )


        total_inserted += inserted

        total_duplicates += duplicates




    print(
        "\n=============================="
    )

    print(
        "TOTAL"
    )

    print(
        "=============================="
    )


    print(
        f"Inserted : {total_inserted}"
    )

    print(
        f"Duplicates : {total_duplicates}"
    )




if __name__ == "__main__":

    main()