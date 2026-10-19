"""
Rule-based tagging for job listings.

The listings table has work_style / type / category / skills / experience_level
columns that, until now, were never actually populated — every row just got
the schema's hardcoded default (e.g. every single listing showed as
'Internship' / 'Technology' / 'Entry Level' regardless of what it actually was).
That made the Type/Skills filters on the frontend cosmetic — they existed in
the UI but had no real data to filter against.

This module replaces the defaults with a real (if imperfect) keyword-based
classifier run against each listing's title + summary. It's not an LLM and
won't catch everything, but it's grounded in the actual text of each posting
instead of being a static placeholder. Phase 3 of the original build plan
(Gemini-based tagging) is still the natural upgrade path for the cases this
keyword approach gets wrong.
"""

import re

SKILL_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "React", "React Native", "Node.js",
    "SQL", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Java", "C++", "C#",
    "Go", "Ruby", "PHP", "Kotlin", "Swift", "Django", "Flask", "REST API",
    "CI/CD", "Git", "Linux", "HTML", "CSS", ".NET", "DevOps", "Terraform",
    "Salesforce", "SAP", "Tableau", "Power BI", "Figma", "Machine Learning",
    "Data Analysis", "Excel", "Product Management", "SEO", "Accounting",
]

_SENIOR_PAT = re.compile(r"\b(senior|sr\.?|principal|staff|lead|director|head of)\b", re.I)
_ENTRY_PAT = re.compile(
    r"\b(junior|jr\.?|graduate|trainee|entry.?level|intern(ship)?|praktikum|werkstudent|working student)\b",
    re.I,
)
_INTERN_TYPE_PAT = re.compile(
    r"\b(intern(ship)?|praktikum|werkstudent|working student|trainee)\b", re.I
)
_CONTRACT_PAT = re.compile(r"\b(contract|contractor|freelance)\b", re.I)
_PARTTIME_PAT = re.compile(r"\b(part.?time|teilzeit)\b", re.I)
_HYBRID_PAT = re.compile(r"\bhybrid\b", re.I)
_ONSITE_PAT = re.compile(r"\b(on.?site|onsite|vor ort|in.office)\b", re.I)

_CATEGORY_RULES = [
    ("Marketing", re.compile(r"\b(marketing|seo|social media|brand|content)\b", re.I)),
    ("Sales", re.compile(r"\b(sales|account executive|business development|key account)\b", re.I)),
    ("Finance", re.compile(r"\b(finance|accounting|rechnungswesen|fibu|bilanzbuchhalter|steuerfach|tax)\b", re.I)),
    ("Consulting", re.compile(r"\b(consult(ant|ing))\b", re.I)),
    ("Design", re.compile(r"\b(design(er)?|ux|ui)\b", re.I)),
    ("Customer Support", re.compile(r"\b(customer (support|service)|support engineer)\b", re.I)),
    ("HR", re.compile(r"\b(hr|human resources|recruit(er|ing))\b", re.I)),
    ("Operations", re.compile(r"\b(operations|project (manager|coordinator)|projektleiter|projektkoordinator)\b", re.I)),
]
_TECH_PAT = re.compile(
    r"\b(engineer|developer|entwickler|software|programmer|backend|frontend|fullstack|full.stack|devops|quality assurance|data scientist|data analyst|data engineer)\b",
    re.I,
)


def infer_tags(title: str, summary: str = "", remote_flag: int = 0) -> dict:
    title = title or ""
    summary = summary or ""
    text = f"{title} {summary}"

    # --- experience_level (title-weighted; title is far more reliable than summary noise) ---
    if _SENIOR_PAT.search(title):
        experience_level = "Senior"
    elif _ENTRY_PAT.search(title):
        experience_level = "Entry Level"
    elif _SENIOR_PAT.search(summary):
        experience_level = "Senior"
    elif _ENTRY_PAT.search(summary):
        experience_level = "Entry Level"
    else:
        experience_level = "Mid Level"

    # --- type (employment type) ---
    if _INTERN_TYPE_PAT.search(title) or _INTERN_TYPE_PAT.search(summary):
        job_type = "Internship"
    elif _CONTRACT_PAT.search(text):
        job_type = "Contract"
    elif _PARTTIME_PAT.search(text):
        job_type = "Part-time"
    else:
        job_type = "Full-time"

    # --- work_style ---
    if remote_flag:
        work_style = "Remote"
    elif _HYBRID_PAT.search(text):
        work_style = "Hybrid"
    elif _ONSITE_PAT.search(text):
        work_style = "On-site"
    else:
        work_style = "On-site"

    # --- category ---
    # Check explicit domain role-titles first (e.g. "Marketing Manager",
    # "Account Executive") since those are stronger, more specific signals
    # than a loose tech pattern. Only fall back to the broader tech check,
    # then a summary-level scan, if the title itself is ambiguous.
    category = None
    for label, pat in _CATEGORY_RULES:
        if pat.search(title):
            category = label
            break
    if category is None and _TECH_PAT.search(title):
        category = "Technology"
    if category is None:
        for label, pat in _CATEGORY_RULES:
            if pat.search(summary):
                category = label
                break
    if category is None:
        category = "Technology" if _TECH_PAT.search(summary) else "Other"

    # --- skills (matched keywords present in title/summary) ---
    found = []
    for kw in SKILL_KEYWORDS:
        pat = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
        if pat.search(text):
            found.append(kw)
    skills = ", ".join(found)

    return {
        "work_style": work_style,
        "type": job_type,
        "category": category,
        "skills": skills,
        "experience_level": experience_level,
    }
