from app.scoring import score_lead,choose_owner
def test_hot():
 s,p=score_lead({"budget":6000,"company":"Acme","interest":"api integration","country":"US"});assert s>=75 and p=="hot"
def test_low():
 s,p=score_lead({"budget":50,"company":"","interest":"","country":""});assert s<75
def test_route():assert choose_owner({"interest":"FastAPI"},80)=="Backend Team"
