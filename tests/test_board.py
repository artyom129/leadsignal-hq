from datetime import timedelta

import pytest

from app import services
from app.scoring import breakdown, score_lead

GOOD = {"name": "Ann Lee", "email": "ann@example.com", "company": "Acme", "country": "US",
        "budget": 6000, "interest": "fastapi"}


@pytest.mark.parametrize("lead", [
    GOOD,
    {"budget": 0},
    {"budget": 700, "interest": "web scraping", "country": "JP", "company": "Kumo"},
    {"budget": 2500, "interest": "automation", "country": "DE"},
])
def test_breakdown_adds_up_to_the_score(lead):
    assert sum(points for _, _, points in breakdown(lead)) == score_lead(lead)[0]


def test_breakdown_explains_each_part():
    reasons = {key: reason for key, reason, _ in breakdown(GOOD)}
    assert reasons["budget"] == "Budget $5,000+"
    assert reasons["interest"] == "Core service: fastapi"
    assert reasons["country"] == "Priority market: US"


def test_search_treats_percent_and_underscore_as_text(db):
    services.create_lead(db, {**GOOD, "company": "100% Growth"})
    services.create_lead(db, {"name": "Bo", "email": "bo@x.com", "company": "Plain"})
    assert services.search(db, q="100%")[1] == 1
    assert services.search(db, q="%")[1] == 1
    assert services.search(db, q="_")[1] == 0


def test_board_orders_and_places_leads(db):
    hot, _ = services.create_lead(db, GOOD)
    normal, _ = services.create_lead(db, {"name": "Bo", "email": "bo@x.com"})
    answered, _ = services.create_lead(db, {"name": "Cy", "email": "cy@x.com"})
    services.set_status(db, answered.id, "contacted")

    now = hot.created_at + timedelta(minutes=20)  # hot SLA is 15 min: 5 min late
    board = services.response_board(services.search(db)[0], now)
    names = [item["lead"].name for item in board["items"]]
    assert names == ["Ann Lee", "Bo"]  # answered leads are not on the board
    late, waiting = board["items"]
    assert late["late"] and late["left"] == -5 and 0 <= late["position"] < 20
    assert not waiting["late"] and 20 < waiting["position"] <= 100


def test_board_scale_gives_room_to_the_next_minutes():
    assert services.board_position(0) == 20
    assert services.board_position(15) == 40
    assert services.board_position(60) == 60
    assert services.board_position(240) == 100
    assert services.board_position(-60) == 0


def test_activity_reads_like_sentences(db):
    lead, _ = services.create_lead(db, GOOD)
    services.set_status(db, lead.id, "won")
    lines = services.recent_activity(db)
    assert lines[0]["name"] == "Ann Lee" and lines[0]["verb"] == "moved"
    assert lines[1]["verb"] == "came in"


def test_lead_page_and_404(client):
    lid = client.post("/leads", json=GOOD).json()["lead"]["id"]
    page = client.get(f"/leads/{lid}")
    assert page.status_code == 200
    assert "Where the score comes from" in page.text and "Core service: fastapi" in page.text
    missing = client.get("/leads/999")
    assert missing.status_code == 404 and "Nothing here" in missing.text
    assert client.get("/api/leads/999").json() == {"detail": "Lead not found"}


def test_status_form_returns_to_the_lead(client):
    lid = client.post("/leads", json=GOOD).json()["lead"]["id"]
    assert client.post(f"/leads/{lid}/status/won").headers["location"] == f"/leads/{lid}"
