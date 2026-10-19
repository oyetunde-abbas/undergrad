import sqlite3

import pytest

import db, drafter, onboarding
from test_expiry import conn_db, L, row  # noqa: F401  (shared fixtures/helpers)
from migrate_add_expiry import migrate


@pytest.fixture
def pdb(conn_db):
    c = sqlite3.connect(conn_db)
    c.execute("""CREATE TABLE profile (user_id INTEGER PRIMARY KEY, about TEXT DEFAULT '', skills TEXT DEFAULT '[]',
        resume_filename TEXT, resume_original_name TEXT, resume_uploaded_at TIMESTAMP, resume_text TEXT, updated_at TIMESTAMP)""")
    migrate(c); c.close()
    return conn_db


# ---------- onboarding validation + persistence
def test_clean_accepts_valid_and_never_defaults_degree():
    out = onboarding.clean({"stage": "serving", "field": "finance", "locations": ["lagos", "lagos"], "tracks": ["data"]})
    assert out == {"stage": "serving", "field": "finance", "locations": ["lagos"], "tracks": ["data"]}
    assert "degree" not in out

@pytest.mark.parametrize("bad", [{"stage": "ceo"}, {"field": "x"}, {"degree": "4.0"}, {"locations": ["mars"]},
                                 {"tracks": ["data", "data2", "x", "y"]}, "string", {"locations": "lagos"}])
def test_clean_rejects_garbage(bad):
    with pytest.raises(ValueError):
        onboarding.clean(bad)

def test_skip_is_stored_as_skip():
    assert onboarding.clean({"skipped": True, "stage": "serving"}) == {"skipped": True}

def test_onboarding_persists_on_profile(pdb):
    assert db.get_profile(1)["onboarding"] is None
    db.update_profile(1, onboarding={"stage": "final_year", "field": "tech_design"})
    assert db.get_profile(1)["onboarding"] == {"stage": "final_year", "field": "tech_design"}
    db.update_profile(1, about="hi")                      # unrelated edit keeps it
    assert db.get_profile(1)["onboarding"]["stage"] == "final_year"


# ---------- ranking
def seed_rank(conn):
    db.insert_listing(L("fin", title="Audit Trainee", company="A", summary="Audit and tax. Corps members are welcome to apply.", location="Lagos"))
    db.insert_listing(L("dev", title="Software Developer", company="B", summary="Python developer.", location="Abuja"))
    db.insert_listing(L("post", title="Accountant", company="C", summary="NYSC discharge certificate is required. Finance role.", location="Lagos"))
    db.insert_listing(L("top", title="Finance Analyst", company="D", summary="Minimum of 2:1 required. Finance.", location="Lagos"))

def test_ranking_prefers_field_track_location_and_hides_post_nysc_for_corper(pdb):
    seed_rank(pdb)
    prefs = {"stage": "serving", "field": "finance", "locations": ["lagos"], "tracks": ["audit_finance"]}
    ranked = onboarding.rank_for_you(db.get_jobs, prefs)
    urls = [j["apply_url"] for j in ranked]
    assert urls[0] == "fin" and "post" not in urls and "dev" not in urls
    assert "Corps members welcome" in ranked[0]["match_reasons"]

def test_ranking_hides_roles_above_my_degree_only_when_stated(pdb):
    seed_rank(pdb)
    base = {"stage": "graduate", "field": "finance", "locations": ["lagos"], "tracks": ["audit_finance"]}
    assert "top" in [j["apply_url"] for j in onboarding.rank_for_you(db.get_jobs, base)]          # no degree given -> no hiding
    assert "top" not in [j["apply_url"] for j in onboarding.rank_for_you(db.get_jobs, {**base, "degree": "2:2"})]
    assert "top" in [j["apply_url"] for j in onboarding.rank_for_you(db.get_jobs, {**base, "degree": "first"})]

def test_ranking_never_returns_closed(pdb):
    seed_rank(pdb); db.close_listing_by_url("fin")
    prefs = {"stage": "serving", "field": "finance", "tracks": ["audit_finance"]}
    assert "fin" not in [j["apply_url"] for j in onboarding.rank_for_you(db.get_jobs, prefs)]


# ---------- drafter
@pytest.mark.parametrize("text,expected", [
    ("Send CVs to careers@acme.com.ng today", "careers@acme.com.ng"),
    ("info@acme.com or hr@acme.com", "hr@acme.com"),
    ("write to noreply@acme.com", None),
    ("logo@2x.png", None), ("no email here", None)])
def test_email_extraction(text, expected):
    assert drafter.extract_hr_email(text) == expected

JOB = {"title": "Graduate Trainee", "company": "Acme", "summary": "Apply to careers@acme.com", "apply_url": "https://acme.com/j"}

def test_template_has_no_default_grade_and_no_nysc_claim(monkeypatch):
    monkeypatch.setattr(drafter, "is_llm_available", lambda: False)
    d = drafter.build_draft(JOB, "Chidi Okafor", {"skills": ["Excel", "SQL"]}, {}, None)
    assert d["method"] == "email" and d["to_email"] == "careers@acme.com" and not d["ai_used"]
    assert "2:1" not in d["body"] and "First Class" not in d["body"] and "NYSC" not in d["body"]
    assert "Excel" in d["body"] and "Chidi Okafor" in d["body"]
    assert any("CV" in n for n in d["notes"])

def test_degree_only_when_student_chose_one(monkeypatch):
    monkeypatch.setattr(drafter, "is_llm_available", lambda: False)
    d = drafter.build_draft(JOB, "Ada", {}, {"degree": "2:2"}, None)
    assert "Second Class Lower (2:2)" in d["body"]

def test_ai_draft_that_invents_a_grade_is_rejected(monkeypatch):
    monkeypatch.setattr(drafter, "is_llm_available", lambda: True)
    monkeypatch.setattr(drafter, "generate_json", lambda *a, **k: {"subject": "Hi", "body": "I graduated with a First Class degree."})
    d = drafter.build_draft(JOB, "Ada", {"skills": ["Excel"]}, {}, None)
    assert not d["ai_used"] and "First Class" not in d["body"]

def test_ai_draft_that_is_clean_is_used(monkeypatch):
    monkeypatch.setattr(drafter, "is_llm_available", lambda: True)
    monkeypatch.setattr(drafter, "generate_json", lambda *a, **k: {"subject": "Application", "body": "Dear team, I use Excel. CV attached."})
    d = drafter.build_draft(JOB, "Ada", {"skills": ["Excel"]}, {}, "resume text")
    assert d["ai_used"] and d["subject"] == "Application"

def test_ai_nysc_claim_rejected_unless_serving(monkeypatch):
    monkeypatch.setattr(drafter, "is_llm_available", lambda: True)
    monkeypatch.setattr(drafter, "generate_json", lambda *a, **k: {"subject": "s", "body": "I have my NYSC discharge certificate."})
    assert not drafter.build_draft(JOB, "Ada", {}, {"stage": "graduate"}, None)["ai_used"]

def test_portal_when_no_email(monkeypatch):
    monkeypatch.setattr(drafter, "is_llm_available", lambda: False)
    d = drafter.build_draft({**JOB, "summary": "Apply on our portal"}, "Ada", {}, {}, None)
    assert d["method"] == "portal" and d["to_email"] is None and "[Your name]" not in d["body"]
