import sqlite3
from datetime import timedelta

import pytest

import db
import expiry
from expiry import fmt, utcnow, parse_deadline, default_expiry, dedupe_key, decorate
from migrate_add_expiry import migrate


@pytest.fixture
def conn_db(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT, summary TEXT,
        apply_url TEXT UNIQUE, deadline TEXT, location TEXT, remote INTEGER DEFAULT 0,
        work_style TEXT, type TEXT DEFAULT 'Internship', category TEXT DEFAULT 'Technology',
        skills TEXT, experience_level TEXT DEFAULT 'Entry Level', nysc_free INTEGER DEFAULT 0,
        eligibility_notes TEXT, source TEXT, content_hash TEXT, status TEXT DEFAULT 'active',
        needs_manual_review INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE saved_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, listing_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, listing_id));
    CREATE TABLE applications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, listing_id INTEGER,
        title TEXT NOT NULL, company TEXT, location TEXT, status TEXT DEFAULT 'Applied', applied_date TEXT,
        notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    """)
    migrate(c)
    c.close()
    return path


def L(url, **kw):
    base = {"title": "Graduate Trainee", "company": "Acme Ltd", "apply_url": url,
            "source": "jobberman", "type": "Graduate", "deadline": None}
    base.update(kw)
    return base


def row(url):
    c = db.get_conn()
    r = c.execute("SELECT * FROM listings WHERE apply_url=?", (url,)).fetchone()
    c.close()
    return dict(r)


def shift(url, **cols):
    c = db.get_conn()
    for k, v in cols.items():
        c.execute(f"UPDATE listings SET {k}=? WHERE apply_url=?", (v, url))
    c.commit(); c.close()


# ---------- deadline parsing
@pytest.mark.parametrize("text", ["30 November, 2026", "November 30, 2026", "30th Nov 2026", "30/11/2026", "2026-11-30"])
def test_parses_common_formats_as_end_of_day_wat(text):
    # 23:59:59 in Nigeria (UTC+1) == 22:59:59 UTC
    assert parse_deadline(text) == "2026-11-30 22:59:59"

def test_day_first_ambiguity_is_nigerian_style():
    assert parse_deadline("03/11/2026").startswith("2026-11-03")

@pytest.mark.parametrize("text", [None, "", "ASAP", "Open until filled", "rolling basis", "soon", "1999-01-01", "2090-01-01"])
def test_never_guesses(text):
    assert parse_deadline(text) is None

def test_iso_with_time_and_zone():
    assert parse_deadline("2026-11-30T12:00:00Z") == "2026-11-30 12:00:00"


# ---------- default lifetime
def test_default_lifetimes():
    t = utcnow()
    assert default_expiry(t, "Internship") == fmt(t + timedelta(days=21))
    assert default_expiry(t, "Full-time") == fmt(t + timedelta(days=30))

def test_insert_without_deadline_gets_default_expiry(conn_db):
    db.insert_listing(L("u1"))
    r = row("u1")
    assert r["status"] == "active" and r["expires_at"] and r["first_seen_at"]

def test_rescrape_does_not_extend_default_expiry(conn_db):
    db.insert_listing(L("u1"))
    before = row("u1")["expires_at"]
    db.insert_listing(L("u1"))
    assert row("u1")["expires_at"] == before


# ---------- feed filtering
def test_expired_hidden_from_feed_but_row_kept(conn_db):
    db.insert_listing(L("u1"))
    db.insert_listing(L("u2", title="Other", company="Other Co"))
    shift("u1", expires_at=fmt(utcnow() - timedelta(hours=1)))
    urls = {j["apply_url"] for j in db.get_jobs()}
    assert urls == {"u2"} and db.count_jobs() == 1
    assert db.get_job(row("u1")["id"])["is_closed"] is True   # detail still works

def test_past_real_deadline_inserts_as_expired(conn_db):
    db.insert_listing(L("u1", deadline="1 January 2026"))
    assert db.count_jobs() == 0 and row("u1")["status"] == "expired"

def test_new_later_deadline_reactivates(conn_db):
    db.insert_listing(L("u1", deadline="1 January 2026"))
    future = (utcnow() + timedelta(days=10)).strftime("%d %B %Y")
    db.insert_listing(L("u1", deadline=future))
    assert row("u1")["status"] == "active" and db.count_jobs() == 1

def test_sweep(conn_db):
    db.insert_listing(L("u1"))
    shift("u1", expires_at=fmt(utcnow() - timedelta(days=1)))
    assert db.expire_listings() == 1 and row("u1")["status"] == "expired"


# ---------- missed-scrape tracking
def seed(n, source="jobberman"):
    for i in range(n):
        db.insert_listing(L(f"{source}/{i}", title=f"Role {i}", company=f"Co {i}", source=source))

def old(source="jobberman"):
    c = db.get_conn()
    c.execute("UPDATE listings SET last_seen_at='2020-01-01 00:00:00' WHERE source=?", (source,))
    c.commit(); c.close()

def scrape(seen_idx, complete=True, source="jobberman"):
    run = db.begin_scrape(source)
    db.touch_listings([f"{source}/{i}" for i in seen_idx])
    return db.finish_scrape(run, complete)

def test_closed_after_two_consecutive_complete_scrapes(conn_db):
    seed(30); old()
    s1 = scrape(range(29))                     # #29 missing once
    assert s1["counted"] and row("jobberman/29")["status"] == "active"
    old(); 
    s2 = scrape(range(29))                     # missing twice
    assert row("jobberman/29")["status"] == "closed" and row("jobberman/0")["status"] == "active"

def test_reappearing_resets_counter(conn_db):
    seed(30); old()
    scrape(range(29)); old()
    scrape(range(30))                          # back again
    assert row("jobberman/29")["missed_scrapes"] == 0 and row("jobberman/29")["status"] == "active"

def test_broken_scrape_never_mass_closes(conn_db):
    seed(30); old()
    s = scrape(range(3))                       # layout changed: saw 3 of 30
    assert not s["counted"] and db.count_jobs() == 30

def test_zero_seen_or_partial_never_closes(conn_db):
    seed(30); old()
    assert not scrape([])["counted"]
    assert not scrape(range(25), complete=False)["counted"]
    assert db.count_jobs() == 30

def test_source_that_says_closed_closes_immediately(conn_db):
    db.insert_listing(L("u1"))
    assert db.close_listing_by_url("u1") and row("u1")["status"] == "closed"

def test_reseen_closed_listing_reopens_if_in_date(conn_db):
    db.insert_listing(L("u1")); db.close_listing_by_url("u1")
    db.touch_listing("u1")
    assert row("u1")["status"] == "active"


# ---------- saved / applications keep closed jobs visible
def test_saved_and_applications_show_closed(conn_db):
    db.insert_listing(L("u1")); lid = row("u1")["id"]
    db.save_job(1, lid)
    db.add_application(1, {"title": "Graduate Trainee", "listing_id": lid})
    shift("u1", expires_at=fmt(utcnow() - timedelta(days=1)))
    saved = db.get_saved_jobs(1)
    assert len(saved) == 1 and saved[0]["is_closed"] and saved[0]["closed_reason"] == "deadline_passed"
    apps = db.get_applications(1)
    assert apps[0]["listing_closed"] is True and apps[0]["status"] == "Applied"  # stage untouched

def test_application_without_listing_is_not_closed(conn_db):
    db.add_application(1, {"title": "Manual entry"})
    assert db.get_applications(1)[0]["listing_closed"] is False


# ---------- closing soon
def test_closing_soon_flag():
    soon = decorate({"status": "active", "expires_at": fmt(utcnow() + timedelta(days=2)), "last_seen_at": fmt(utcnow() - timedelta(days=2))})
    later = decorate({"status": "active", "expires_at": fmt(utcnow() + timedelta(days=9))})
    assert soon["closing_soon"] and not later["closing_soon"] and soon["checked_days_ago"] == 2


# ---------- duplicates
def test_dedupe_key_normalises():
    assert dedupe_key("Graduate Trainee!", "Acme Nigeria Ltd") == dedupe_key("graduate trainee", "ACME")
    assert dedupe_key("Graduate Trainee", None) is None

def test_cross_source_duplicate_hidden(conn_db):
    db.insert_listing(L("a", source="jobberman"))
    db.insert_listing(L("b", source="myjobmag"))
    assert db.count_jobs() == 1
    assert {j["apply_url"] for j in db.get_jobs()} == {"a"}

def test_duplicate_reappears_if_original_expires(conn_db):
    db.insert_listing(L("a")); db.insert_listing(L("b", source="myjobmag"))
    shift("a", expires_at=fmt(utcnow() - timedelta(days=1)))
    assert {j["apply_url"] for j in db.get_jobs()} == {"b"}


# ---------- reports
def test_reports_hide_after_three_distinct_users(conn_db):
    db.insert_listing(L("u1")); lid = row("u1")["id"]
    assert not db.report_listing(1, lid, "scam")["hidden"]
    assert db.report_listing(1, lid)["new_report"] is False      # same user twice
    db.report_listing(2, lid)
    r = db.report_listing(3, lid)
    assert r["hidden"] and db.count_jobs() == 0 and row("u1")["status"] == "under_review"

def test_admin_restore(conn_db):
    db.insert_listing(L("u1")); lid = row("u1")["id"]
    for u in (1, 2, 3): db.report_listing(u, lid)
    assert db.set_listing_status(lid, "active") and db.count_jobs() == 1

def test_rescrape_does_not_resurrect_reported(conn_db):
    db.insert_listing(L("u1")); lid = row("u1")["id"]
    for u in (1, 2, 3): db.report_listing(u, lid)
    db.insert_listing(L("u1"))
    assert row("u1")["status"] == "under_review"


# ---------- sync keeps scraper-machine lifecycle
def test_sync_preserves_closed_status_and_timestamps(conn_db):
    payload = L("u1", status="closed", first_seen_at="2026-09-01 10:00:00",
                last_seen_at="2026-09-20 10:00:00", expires_at="2026-10-01 10:00:00")
    db.insert_listing(payload, from_sync=True)
    r = row("u1")
    assert r["status"] == "closed" and r["last_seen_at"] == "2026-09-20 10:00:00"
    db.insert_listing(payload, from_sync=True)     # re-sync must not "freshen" it
    assert row("u1")["last_seen_at"] == "2026-09-20 10:00:00" and db.count_jobs() == 0

def test_sync_never_overwrites_under_review(conn_db):
    db.insert_listing(L("u1")); lid = row("u1")["id"]
    for u in (1, 2, 3): db.report_listing(u, lid)
    db.insert_listing(L("u1", status="active"), from_sync=True)
    assert row("u1")["status"] == "under_review"


# ---------- housekeeping / migration
def test_purge_keeps_anything_referenced(conn_db):
    db.insert_listing(L("keep", title="A", company="A")); db.insert_listing(L("drop", title="B", company="B"))
    keep_id = row("keep")["id"]; db.save_job(1, keep_id)
    old_ts = fmt(utcnow() - timedelta(days=400))
    shift("keep", status="expired", closed_at=old_ts); shift("drop", status="expired", closed_at=old_ts)
    assert db.purge_stale_listings(180) == 1
    assert row("keep")

def test_migration_backfill_gives_grace_not_instant_wipe(tmp_path):
    path = tmp_path / "m.db"; c = sqlite3.connect(path)
    c.execute("""CREATE TABLE listings (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT, summary TEXT, apply_url TEXT UNIQUE,
        deadline TEXT, type TEXT, source TEXT, status TEXT DEFAULT 'active', created_at TIMESTAMP)""")
    c.execute("INSERT INTO listings(title,company,apply_url,type,created_at) VALUES('Old','X','a','Graduate','2025-01-01 00:00:00')")
    c.execute("INSERT INTO listings(title,company,apply_url,deadline,type,created_at) VALUES('Dead','Y','b','1 March 2025','Graduate','2025-01-01 00:00:00')")
    c.commit()
    assert migrate(c) == 2 and migrate(c) == 0          # idempotent
    a, b = [dict(zip(("status", "expires_at"), r)) for r in c.execute("SELECT status, expires_at FROM listings ORDER BY id")]
    assert a["status"] == "active" and a["expires_at"] > fmt(utcnow())   # grace window
    assert b["status"] == "expired"                                      # real past deadline is honoured


# ---------- scam guard
import scam_guard, eligibility

@pytest.mark.parametrize("text", [
    "Pay N5,000 registration fee to secure your slot", "Candidates are required to pay for training",
    "Send N2,500 to account 0123456789", "Purchase the application form at our office", "A refundable deposit is required"])
def test_scam_phrases_flagged(text):
    assert scam_guard.check(text)

@pytest.mark.parametrize("text", [
    "No registration fee required", "We pay for medical insurance and training for staff",
    "You will not be asked to pay for training", "Competitive salary and payment of bonuses", "Candidates must have a BSc in Accounting"])
def test_legit_text_not_flagged(text):
    assert scam_guard.check(text) is None

def test_scam_listing_is_hidden_and_listed_for_admin(conn_db):
    db.insert_listing(L("s1", summary="Applicants must pay a N3,000 processing fee before interview."))
    r = row("s1")
    assert r["status"] == "under_review" and r["flag_reason"] and db.count_jobs() == 0
    assert [x["id"] for x in db.get_reported_listings()] == [r["id"]]

def test_admin_restore_survives_rescrape(conn_db):
    s = "Applicants must pay a N3,000 processing fee."
    db.insert_listing(L("s1", summary=s)); lid = row("s1")["id"]
    db.set_listing_status(lid, "active")
    db.insert_listing(L("s1", summary=s))
    assert row("s1")["status"] == "active"          # human said it's fine; don't re-flag

def test_active_listing_flagged_on_rescrape(conn_db):
    db.insert_listing(L("s1", summary="Great role."))
    db.insert_listing(L("s1", summary="Pay a registration fee to proceed."))
    assert row("s1")["status"] == "under_review"


# ---------- eligibility
def test_eligibility_stored_and_filterable(conn_db):
    db.insert_listing(L("a", title="A", company="A", summary="Minimum of 2:1 required. NYSC discharge certificate is required."))
    db.insert_listing(L("b", title="B", company="B", summary="Open to HND holders. Corps members are welcome to apply."))
    db.insert_listing(L("c", title="C", company="C", summary="Great role, no specifics."))
    assert row("a")["min_degree"] == "2:1" and row("a")["nysc_req"] == "post_nysc"
    assert {j["apply_url"] for j in db.get_jobs(nysc="accepted")} == {"b"}
    assert {j["apply_url"] for j in db.get_jobs(nysc="post")} == {"a"}
    # a 2:2 graduate: hide the 2:1-only role, KEEP the one that states nothing
    assert {j["apply_url"] for j in db.get_jobs(my_degree="2:2")} == {"b", "c"}
    assert db.count_jobs(my_degree="2:2") == 2
    assert {j["apply_url"] for j in db.get_jobs(my_degree="first")} == {"a", "b", "c"}

def test_migration_backfills_flags_and_eligibility(tmp_path):
    path = tmp_path / "m2.db"; c = sqlite3.connect(path)
    c.execute("""CREATE TABLE listings (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT, summary TEXT, apply_url TEXT UNIQUE,
        deadline TEXT, type TEXT, source TEXT, status TEXT DEFAULT 'active', created_at TIMESTAMP)""")
    now = fmt(utcnow())
    c.execute("INSERT INTO listings(title,company,summary,apply_url,type,created_at) VALUES('T','C','Minimum 2:1. Pay a registration fee.','a','Graduate',?)", (now,))
    c.commit(); migrate(c)
    r = c.execute("SELECT status, min_degree, flag_reason FROM listings").fetchone()
    assert r[0] == "under_review" and r[1] == "2:1" and r[2]
