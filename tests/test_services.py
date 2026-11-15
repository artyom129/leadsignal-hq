from datetime import timedelta

import pytest
from sqlalchemy import inspect

from app import services
from app.models import Event, Lead

GOOD = {"name": "Ann Lee", "email": "Ann@Example.com ", "company": "Acme", "country": "US",
        "budget": 6000, "interest": "fastapi"}


@pytest.mark.parametrize("email", ["", "plain", "a@b", "a b@c.com", "@x.com", "a@.c"])
def test_bad_email(email):
    with pytest.raises(services.LeadError):
        services.clean_payload({**GOOD, "email": email})


@pytest.mark.parametrize("budget", [-1, "abc", "nan", "inf", "-inf"])
def test_bad_budget(budget):
    with pytest.raises(services.LeadError):
        services.clean_payload({**GOOD, "budget": budget})


def test_blank_name():
    with pytest.raises(services.LeadError):
        services.clean_payload({**GOOD, "name": "   "})


def test_normalizes():
    p = services.clean_payload({**GOOD, "name": "  Ann   Lee "})
    assert p["email"] == "ann@example.com" and p["name"] == "Ann Lee"


def test_empty_budget_string_is_zero():
    assert services.clean_payload({**GOOD, "budget": ""})["budget"] == 0


def test_create_and_duplicate(db):
    lead, created = services.create_lead(db, GOOD)
    assert created and lead.priority == "hot" and lead.owner == "Backend Team" and lead.sla_minutes == 15
    again, created2 = services.create_lead(db, {**GOOD, "email": "ANN@example.com", "name": "Other"})
    assert not created2 and again.id == lead.id
    assert db.query(Lead).count() == 1
    kinds = [e.event_type for e in db.query(Event).order_by(Event.id)]
    assert kinds == ["lead_created", "duplicate_blocked"]


def test_sla_per_priority(db):
    warm, _ = services.create_lead(db, {"name": "w", "email": "w@x.com", "budget": 500,
                                        "company": "c", "interest": "automation"})
    normal, _ = services.create_lead(db, {"name": "n", "email": "n@x.com"})
    assert (warm.priority, warm.sla_minutes) == ("warm", 60)
    assert (normal.priority, normal.sla_minutes) == ("normal", 240)


def test_email_is_unique_in_database(engine):
    uniq = [i for i in inspect(engine).get_indexes("leads") if i["unique"]]
    assert any(i["column_names"] == ["email"] for i in uniq)


def test_set_status(db):
    lead, _ = services.create_lead(db, GOOD)
    assert services.set_status(db, lead.id, "contacted").status == "contacted"
    services.set_status(db, lead.id, "contacted")  # no change, no extra event
    assert db.query(Event).filter_by(event_type="status_changed").count() == 1
    assert services.set_status(db, 999, "won") is None
    with pytest.raises(services.LeadError):
        services.set_status(db, lead.id, "banana")


def test_overdue_only_for_untouched(db):
    lead, _ = services.create_lead(db, GOOD)
    late = lead.created_at + timedelta(minutes=lead.sla_minutes + 1)
    assert services.is_overdue(lead, late)
    assert services.minutes_left(lead, late) == -1
    assert not services.is_overdue(lead, lead.created_at + timedelta(minutes=lead.sla_minutes - 1))
    services.set_status(db, lead.id, "contacted")
    assert not services.is_overdue(lead, late)


def test_search_and_stats(db):
    services.create_lead(db, GOOD)
    services.create_lead(db, {"name": "Bo", "email": "bo@y.com", "budget": 100})
    leads, total = services.search(db, q="ACME")
    assert total == 1 and leads[0].name == "Ann Lee"
    assert services.search(db, priority="normal")[1] == 1
    assert services.search(db, status="bogus")[1] == 2  # unknown filter is ignored
    assert services.search(db, limit=1, offset=1)[0][0].name == "Ann Lee"
    s = services.stats(db)
    assert s["total"] == 2 and s["hot"] == 1 and s["win_rate"] == 0 and s["pipeline_value"] == 6100
    first = services.search(db)[0][0]
    services.set_status(db, first.id, "won")
    s = services.stats(db)
    assert s["win_rate"] == 100 and s["won"] == 1


def test_stats_empty(db):
    s = services.stats(db)
    assert s["total"] == 0 and s["avg_score"] == 0 and s["win_rate"] == 0


def test_csv_neutralizes_formulas(db):
    services.create_lead(db, {"name": '=HYPERLINK("http://x")', "email": "f@x.com"})
    out = services.to_csv(services.search(db)[0])
    assert "'=HYPERLINK" in out and out.splitlines()[0].startswith("id,created_at")
