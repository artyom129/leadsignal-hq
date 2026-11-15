GOOD = {"name": "Ann Lee", "email": "ann@example.com", "company": "Acme", "country": "US",
        "budget": 6000, "interest": "fastapi"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}


def test_create_then_duplicate(client):
    r = client.post("/leads", json=GOOD)
    assert r.status_code == 200 and r.json()["created"] and r.json()["lead"]["priority"] == "hot"
    r2 = client.post("/leads", json={**GOOD, "email": "ANN@example.com"})
    assert r2.json()["created"] is False and r2.json()["lead"]["id"] == r.json()["lead"]["id"]
    assert len(client.get("/api/leads").json()) == 1


def test_create_rejects_bad_data(client):
    assert client.post("/leads", json={**GOOD, "email": "nope"}).status_code == 422
    assert client.post("/leads", json={**GOOD, "budget": -5}).status_code == 422
    assert client.post("/leads", json={"name": "x"}).status_code == 422
    assert client.get("/api/leads").json() == []


def test_get_one_and_404(client):
    lid = client.post("/leads", json=GOOD).json()["lead"]["id"]
    assert client.get(f"/api/leads/{lid}").json()["email"] == "ann@example.com"
    assert client.get("/api/leads/999").status_code == 404


def test_status_patch(client):
    lid = client.post("/leads", json=GOOD).json()["lead"]["id"]
    r = client.patch(f"/api/leads/{lid}/status", json={"status": "won"})
    assert r.status_code == 200 and r.json()["status"] == "won"
    assert client.patch(f"/api/leads/{lid}/status", json={"status": "nope"}).status_code == 422
    assert client.patch("/api/leads/999/status", json={"status": "won"}).status_code == 404


def test_status_form_route(client):
    lid = client.post("/leads", json=GOOD).json()["lead"]["id"]
    assert client.post(f"/leads/{lid}/status/contacted").status_code == 303
    assert client.post(f"/leads/{lid}/status/zzz").status_code == 422
    assert client.post("/leads/999/status/won").status_code == 404
    assert client.get(f"/api/leads/{lid}").json()["status"] == "contacted"


def test_list_filters_and_paging(client):
    for i in range(5):
        client.post("/leads", json={"name": f"L{i}", "email": f"l{i}@x.com", "budget": 6000 if i < 2 else 0})
    assert len(client.get("/api/leads?priority=warm").json()) == 2
    assert len(client.get("/api/leads?limit=2&offset=4").json()) == 1
    assert client.get("/api/leads?limit=0").status_code == 422
    assert client.get("/api/leads?q=l3").json()[0]["name"] == "L3"


def test_stats_endpoint(client):
    client.post("/leads", json=GOOD)
    s = client.get("/api/stats").json()
    assert s["total"] == 1 and s["by_status"]["new"] == 1


def test_form_submission_messages(client):
    ok = client.post("/leads/form", data={"name": "Bo", "email": "bo@x.com", "budget": "100", "interest": "automation"})
    assert ok.status_code == 303 and "Lead%20created" in ok.headers["location"]
    dup = client.post("/leads/form", data={"name": "Bo", "email": "bo@x.com"})
    assert "duplicate" in dup.headers["location"]
    bad = client.post("/leads/form", data={"name": "Bo", "email": "bad"})
    assert "Not%20saved" in bad.headers["location"]
    bad2 = client.post("/leads/form", data={"name": "Bo", "email": "z@x.com", "budget": "abc"})
    assert "Not%20saved" in bad2.headers["location"]
    assert len(client.get("/api/leads").json()) == 1


def test_dashboard_renders(client):
    client.post("/leads", json=GOOD)
    html = client.get("/").text
    assert "Ann Lee" in html and "min left" in html and "LeadSignal HQ" in html
    assert "No leads match" in client.get("/?q=zzz").text


def test_dashboard_escapes_html(client):
    client.post("/leads", json={**GOOD, "name": "<script>alert(1)</script>"})
    html = client.get("/").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_dashboard_empty_and_message(client):
    html = client.get("/?msg=Hello%20there").text
    assert "Hello there" in html and "No leads match" in html


def test_export_csv(client):
    client.post("/leads", json=GOOD)
    r = client.get("/api/leads/export.csv?status=new")
    assert r.headers["content-type"].startswith("text/csv") and "ann@example.com" in r.text
    assert "ann@example.com" not in client.get("/api/leads/export.csv?status=won").text
