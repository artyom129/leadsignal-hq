import re

HIGH_INTEREST = {"automation", "api integration", "fastapi", "crm integration", "data pipeline"}
PREMIUM_COUNTRIES = {
    "US", "USA", "UNITED STATES", "CA", "CANADA", "UK", "GB", "UNITED KINGDOM",
    "AU", "AUSTRALIA", "DE", "GERMANY", "CH", "SWITZERLAND",
}

# Points, kept in one place so the README table matches the code.
BASE = 20
BUDGET_STEPS = ((5000, 35), (2000, 25), (500, 12))
COMPANY_POINTS = 10
HIGH_INTEREST_POINTS = 20
OTHER_INTEREST_POINTS = 8
COUNTRY_POINTS = 10

SLA_MINUTES = {"hot": 15, "warm": 60, "normal": 240}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def breakdown(p: dict) -> list[tuple[str, str, int]]:
    """(key, human reason, points) for every part of the score, zeros included."""
    budget = float(p.get("budget") or 0)
    budget_points = next((points for limit, points in BUDGET_STEPS if budget >= limit), 0)
    budget_reason = next((f"Budget ${limit:,}+" for limit, points in BUDGET_STEPS if budget >= limit), "Budget under $500")

    interest = " ".join((p.get("interest") or "").lower().split())
    if interest in HIGH_INTEREST:
        interest_points, interest_reason = HIGH_INTEREST_POINTS, f"Core service: {interest}"
    elif interest:
        interest_points, interest_reason = OTHER_INTEREST_POINTS, f"Other interest: {interest}"
    else:
        interest_points, interest_reason = 0, "No interest given"

    has_company = bool((p.get("company") or "").strip())
    country = (p.get("country") or "").strip()
    premium = country.upper() in PREMIUM_COUNTRIES
    return [
        ("base", "Every lead", BASE),
        ("budget", budget_reason, budget_points),
        ("company", "Company named" if has_company else "No company", COMPANY_POINTS if has_company else 0),
        ("interest", interest_reason, interest_points),
        ("country", f"Priority market: {country.upper()}" if premium else "Other market", COUNTRY_POINTS if premium else 0),
    ]


def score_lead(p: dict) -> tuple[int, str]:
    score = min(sum(points for _, _, points in breakdown(p)), 100)
    return score, priority_for(score)


def priority_for(score: int) -> str:
    return "hot" if score >= 75 else "warm" if score >= 50 else "normal"


def choose_owner(p: dict, score: int) -> str:
    # Whole words only: "capital" must not count as "api".
    words = _words(p.get("interest") or "")
    if words & {"api", "fastapi", "backend"}:
        return "Backend Team"
    if words & {"automation", "crm", "pipeline"}:
        return "Automation Team"
    return "Senior Sales" if score >= 75 else "Sales Queue"
