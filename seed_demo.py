"""Fill the database with a few demo leads. Safe to run again: it resets the data."""
from datetime import timedelta

from app import services
from app.db import SessionLocal, init_db
from app.models import Event, Lead, utcnow

SAMPLES = [
    {"source": "Meta Ads", "name": "Olivia Chen", "email": "olivia@northpeak.io", "company": "NorthPeak", "country": "US", "budget": 6500, "interest": "api integration", "age": 40},
    {"source": "Website", "name": "Daniel Ruiz", "email": "daniel@atlascrm.co", "company": "Atlas CRM", "country": "UK", "budget": 3000, "interest": "crm integration", "age": 20},
    {"source": "LinkedIn", "name": "Mia Novak", "email": "mia@brightops.eu", "company": "BrightOps", "country": "DE", "budget": 1800, "interest": "automation", "age": 5},
    {"source": "Referral", "name": "Noah Kim", "email": "noah@example.com", "company": "", "country": "CA", "budget": 400, "interest": "web scraping", "age": 90},
    {"source": "Google Ads", "name": "Sophia Patel", "email": "sophia@dataforge.ai", "company": "DataForge", "country": "US", "budget": 9000, "interest": "data pipeline", "age": 2},
    {"source": "Website", "name": "Liam Berg", "email": "liam@nordlager.se", "company": "Nordlager", "country": "SE", "budget": 2500, "interest": "fastapi", "age": 300},
    {"source": "Website", "name": "Aigerim Sadykova", "email": "aigerim@steppe.kz", "company": "Steppe Logistics", "country": "KZ", "budget": 4200, "interest": "automation", "age": 70},
    {"source": "LinkedIn", "name": "Ethan Brooks", "email": "ethan@ledgerline.com", "company": "LedgerLine", "country": "US", "budget": 2200, "interest": "crm integration", "age": 9},
    {"source": "Meta Ads", "name": "Hana Sato", "email": "hana@kumo.jp", "company": "Kumo", "country": "JP", "budget": 700, "interest": "web scraping", "age": 30},
    {"source": "Google Ads", "name": "Lucas Meyer", "email": "lucas@feldwerk.de", "company": "Feldwerk", "country": "DE", "budget": 12000, "interest": "api integration", "age": 11},
    {"source": "Website", "name": "Amara Okafor", "email": "amara@greenmile.ng", "company": "", "country": "NG", "budget": 300, "interest": "automation", "age": 150},
    {"source": "Referral", "name": "Chloe Martin", "email": "chloe@pixelpost.fr", "company": "PixelPost", "country": "FR", "budget": 1500, "interest": "data pipeline", "age": 52},
    {"source": "API", "name": "Ravi Iyer", "email": "ravi@quanta.in", "company": "Quanta", "country": "IN", "budget": 5000, "interest": "fastapi", "age": 600},
    {"source": "LinkedIn", "name": "Emma Wilson", "email": "emma@harbor.co.uk", "company": "Harbor", "country": "UK", "budget": 2600, "interest": "automation", "age": 1},
    {"source": "Website", "name": "Timur Abenov", "email": "timur@qazdata.kz", "company": "QazData", "country": "KZ", "budget": 900, "interest": "crm integration", "age": 190},
    {"source": "Google Ads", "name": "Isabella Rossi", "email": "isabella@vela.it", "company": "Vela", "country": "IT", "budget": 3400, "interest": "api integration", "age": 45},
]


def main() -> None:
    init_db()
    db = SessionLocal()
    db.query(Event).delete()
    db.query(Lead).delete()
    db.commit()
    now = utcnow()
    ids = []
    for p in SAMPLES:
        p = dict(p)
        age = p.pop("age")
        lead, _ = services.create_lead(db, p)
        # Back-date the lead and its "came in" event, so the SLA clock shows both states.
        lead.created_at = now - timedelta(minutes=age)
        for event in db.query(Event).filter(Event.lead_id == lead.id):
            event.created_at = lead.created_at
        db.commit()
        ids.append(lead.id)
    for idx, status in ((1, "contacted"), (3, "lost"), (5, "won"), (12, "qualified"), (6, "contacted"), (14, "won")):
        services.set_status(db, ids[idx], status)
    db.close()
    print("Demo data created")


if __name__ == "__main__":
    main()
