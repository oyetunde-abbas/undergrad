print("Starting test...")

import db

print(db.__file__)
print(dir(db))

listing = {
    "title": "Graduate Software Engineer",
    "company": "OpenAI",
    "summary": "Test job listing",
    "apply_url": "https://example.com/job1",
    "location": "Remote",
    "remote": 1,
    "nysc_free": 1,
    "eligibility_notes": "Fresh graduates welcome",
    "source": "test"
}

if db.insert_listing(listing):
    print("Inserted!")
else:
    print("Duplicate!")

print(db.get_all_listings())