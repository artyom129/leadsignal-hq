from app.db import SessionLocal,engine,Base
from app.models import Lead,Event
from app.scoring import score_lead,choose_owner
Base.metadata.create_all(bind=engine)
samples=[
{"source":"Meta Ads","name":"Olivia Chen","email":"olivia@northpeak.io","company":"NorthPeak","country":"US","budget":6500,"interest":"api integration"},
{"source":"Website","name":"Daniel Ruiz","email":"daniel@atlascrm.co","company":"Atlas CRM","country":"UK","budget":3000,"interest":"crm integration"},
{"source":"LinkedIn","name":"Mia Novak","email":"mia@brightops.eu","company":"BrightOps","country":"DE","budget":1800,"interest":"automation"},
{"source":"Referral","name":"Noah Kim","email":"noah@example.com","company":"","country":"CA","budget":400,"interest":"web scraping"},
{"source":"Google Ads","name":"Sophia Patel","email":"sophia@dataforge.ai","company":"DataForge","country":"US","budget":9000,"interest":"data pipeline"}]
db=SessionLocal();db.query(Event).delete();db.query(Lead).delete();db.commit()
for p in samples:
 s,pri=score_lead(p);o=choose_owner(p,s);l=Lead(**p,score=s,priority=pri,owner=o,sla_minutes=15 if pri=="hot" else 60);db.add(l);db.commit();db.refresh(l);db.add(Event(lead_id=l.id,event_type="lead_created",detail=f"{l.name}: {s}/100 → {o}"));db.commit()
db.close();print("Demo data created")
