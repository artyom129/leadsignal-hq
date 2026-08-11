HIGH={"automation","api integration","fastapi","crm integration","data pipeline"}
def score_lead(p):
    s=20; b=float(p.get("budget") or 0)
    s+=35 if b>=5000 else 25 if b>=2000 else 12 if b>=500 else 0
    if (p.get("company") or "").strip(): s+=10
    i=(p.get("interest") or "").strip().lower(); s+=20 if i in HIGH else 8 if i else 0
    if (p.get("country") or "").strip().upper() in {"US","USA","CA","CANADA","UK","GB","AU","AUSTRALIA","DE","CH"}: s+=10
    s=min(s,100); return s,("hot" if s>=75 else "warm" if s>=50 else "normal")
def choose_owner(p,s):
    i=(p.get("interest") or "").lower()
    if "api" in i or "fastapi" in i:return "Backend Team"
    if "automation" in i or "crm" in i:return "Automation Team"
    return "Senior Sales" if s>=75 else "Sales Queue"
