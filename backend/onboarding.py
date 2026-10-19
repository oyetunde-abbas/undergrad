"""
Onboarding answers (4 taps) -> validated, stored on the profile, used to rank
the feed. Nothing here is a hard filter except degree class (and only against
roles that explicitly require a HIGHER class): the rest only re-orders, so a
student never sees an empty feed because of a chip they tapped.
"""

import eligibility

STAGES = {"final_year", "pre_nysc", "serving", "graduate"}
FIELDS = {"tech_design", "finance", "engineering", "business", "health_sciences", "legal_humanities"}
DEGREES = {"first", "2:1", "2:2", "hnd", "ond", "third", "pass"}
LOCATIONS = {"lagos", "abuja", "remote", "anywhere"}
TRACKS = {"graduate_trainee", "product_tech", "data", "audit_finance", "sales_ops", "customer_experience"}

# listing.category values written by tag_listings.py
_FIELD_CATEGORIES = {
    "tech_design": {"Technology", "Design"},
    "finance": {"Finance", "Consulting"},
    "business": {"Sales", "Marketing", "Operations", "Consulting", "HR", "Customer Support"},
}
_FIELD_KEYWORDS = {
    "engineering": ("engineer", "mechanical", "electrical", "civil", "chemical", "technician", "maintenance", "production"),
    "health_sciences": ("pharma", "nurs", "health", "clinical", "laborator", "biochem", "science", "medical", "research"),
    "legal_humanities": ("legal", "law", "compliance", "admin", "communications", "writer", "editor", "public relations", "teacher"),
}
_TRACK_KEYWORDS = {
    "graduate_trainee": ("graduate trainee", "trainee", "graduate"),
    "product_tech": ("product", "software", "developer", "engineer", "frontend", "backend", "tech"),
    "data": ("data", "analyst", "analytics", "insight"),
    "audit_finance": ("audit", "account", "finance", "tax", "treasury", "credit"),
    "sales_ops": ("sales", "operations", "business development", "logistics", "supply"),
    "customer_experience": ("customer", "support", "client", "service"),
}


def clean(data):
    """Validates an onboarding payload. Raises ValueError on anything unexpected."""
    if not isinstance(data, dict):
        raise ValueError("onboarding must be an object")
    if data.get("skipped"):
        return {"skipped": True}

    out = {}
    stage = data.get("stage")
    if stage is not None:
        if stage not in STAGES:
            raise ValueError("invalid stage")
        out["stage"] = stage
    field = data.get("field")
    if field is not None:
        if field not in FIELDS:
            raise ValueError("invalid field")
        out["field"] = field
    degree = data.get("degree")
    if degree not in (None, ""):
        if degree not in DEGREES:
            raise ValueError("invalid degree")
        out["degree"] = degree      # never defaulted: if the student doesn't say, we don't know
    for key, allowed, max_n in (("locations", LOCATIONS, 4), ("tracks", TRACKS, 3)):
        vals = data.get(key)
        if vals is None:
            continue
        if not isinstance(vals, list) or len(vals) > max_n or any(v not in allowed for v in vals):
            raise ValueError(f"invalid {key}")
        out[key] = list(dict.fromkeys(vals))
    return out


def _text(job):
    return f"{job.get('title') or ''} {job.get('summary') or ''}".lower()


def score_job(job, prefs):
    """Returns (score, reasons). Reasons are plain statements the UI can show."""
    score, reasons = 0, []
    field, tracks = prefs.get("field"), prefs.get("tracks") or []
    locs, stage, degree = prefs.get("locations") or [], prefs.get("stage"), prefs.get("degree")
    title = (job.get("title") or "").lower()

    if field in _FIELD_CATEGORIES and job.get("category") in _FIELD_CATEGORIES[field]:
        score += 3; reasons.append("Fits your field")
    elif field in _FIELD_KEYWORDS and any(k in _text(job) for k in _FIELD_KEYWORDS[field]):
        score += 3; reasons.append("Fits your field")

    if any(k in title for t in tracks for k in _TRACK_KEYWORDS.get(t, ())):
        score += 4; reasons.append("Matches a role you picked")

    loc_text = (job.get("location") or "").lower()
    if locs and "anywhere" not in locs:
        if any(l in loc_text for l in locs if l not in ("remote",)) :
            score += 2; reasons.append("In your location")
        elif "remote" in locs and (job.get("remote") or job.get("work_style") == "Remote"):
            score += 2; reasons.append("Remote")

    nysc = job.get("nysc_req")
    if stage in ("pre_nysc", "serving"):
        if nysc == "nysc_ok":
            score += 3; reasons.append("Corps members welcome")
        elif nysc == "post_nysc":
            score -= 6
    elif stage == "graduate" and nysc == "post_nysc":
        score += 1
    elif stage == "final_year" and nysc == "siwes":
        score += 2; reasons.append("Open to students")

    if stage in ("final_year", "graduate", "pre_nysc") and ("trainee" in title or "graduate" in title or "intern" in title):
        score += 1

    if job.get("closing_soon"):
        score += 1
    return score, reasons


def rank_for_you(get_jobs, prefs, limit=10, pool=300):
    """
    Newest `pool` live listings, hide those requiring a higher degree class than
    the student's, score the rest, return the best `limit` (score > 0 only).
    """
    rows = get_jobs(page=1, limit=pool)
    my_tier = eligibility.TIER.get(prefs.get("degree"))
    ranked = []
    for job in rows:
        need = eligibility.TIER.get(job.get("min_degree"))
        if my_tier is not None and need is not None and need > my_tier:
            continue
        score, reasons = score_job(job, prefs)
        if score > 0:
            job["relevance"] = score
            job["match_reasons"] = reasons
            ranked.append(job)
    ranked.sort(key=lambda j: j["relevance"], reverse=True)   # stable: newest first within ties
    return ranked[:limit]
