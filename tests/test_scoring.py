import pytest

from app.scoring import choose_owner, priority_for, score_lead


def test_hot():
    s, p = score_lead({"budget": 6000, "company": "Acme", "interest": "api integration", "country": "US"})
    assert s == 95 and p == "hot"


def test_low():
    s, p = score_lead({"budget": 50, "company": "", "interest": "", "country": ""})
    assert (s, p) == (20, "normal")


def test_score_is_capped():
    s, _ = score_lead({"budget": 1e9, "company": "x", "interest": "automation", "country": "US"})
    assert s == 95  # 20+35+10+20+10 is the real maximum


@pytest.mark.parametrize("budget,points", [(0, 0), (499, 0), (500, 12), (1999, 12), (2000, 25), (4999, 25), (5000, 35)])
def test_budget_steps(budget, points):
    assert score_lead({"budget": budget})[0] == 20 + points


def test_interest_is_case_and_space_insensitive():
    assert score_lead({"interest": "  API   Integration "})[0] == 40
    assert score_lead({"interest": "web scraping"})[0] == 28


def test_country_codes():
    assert score_lead({"country": "de"})[0] == 30
    assert score_lead({"country": "Germany"})[0] == 30
    assert score_lead({"country": "SE"})[0] == 20


def test_priority_thresholds():
    assert [priority_for(x) for x in (49, 50, 74, 75)] == ["normal", "warm", "warm", "hot"]


def test_route_backend():
    assert choose_owner({"interest": "FastAPI"}, 80) == "Backend Team"
    assert choose_owner({"interest": "api integration"}, 10) == "Backend Team"


def test_route_whole_words_only():
    # "capital" contains "api" but is not API work.
    assert choose_owner({"interest": "capital markets"}, 10) == "Sales Queue"
    assert choose_owner({"interest": "rapid prototyping"}, 80) == "Senior Sales"


def test_route_automation_and_pipeline():
    assert choose_owner({"interest": "crm integration"}, 10) == "Automation Team"
    assert choose_owner({"interest": "data pipeline"}, 80) == "Automation Team"


def test_route_sales_by_score():
    assert choose_owner({"interest": "web scraping"}, 75) == "Senior Sales"
    assert choose_owner({"interest": ""}, 74) == "Sales Queue"
