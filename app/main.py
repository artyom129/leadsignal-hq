from datetime import datetime,timedelta
from fastapi import FastAPI,Depends,Request,Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel,ConfigDict
from .db import SessionLocal,engine,Base
from .models import Lead,Event
from .scoring import score_lead,choose_owner
Base.metadata.create_all(bind=engine)
app=FastAPI(title="LeadSignal HQ",version="1.0.0")
templates=Jinja2Templates(directory="templates")
def get_db():
    db=SessionLocal()
    try:yield db
    finally:db.close()
class LeadIn(BaseModel):
    source:str="api"; name:str; email:str; company:str=""; country:str=""; budget:float=0; interest:str=""; notes:str=""
class LeadOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int; source:str; name:str; email:str; company:str; country:str; budget:float; interest:str; score:int; priority:str; owner:str; status:str
def event(db,lid,t,d):db.add(Event(lead_id=lid,event_type=t,detail=d));db.commit()
def upsert(db,p):
    email=p["email"].strip().lower(); ex=db.scalar(select(Lead).where(Lead.email==email))
    if ex:event(db,ex.id,"duplicate_blocked",f"Duplicate ignored from {p.get('source','unknown')}");return ex,False
    s,pri=score_lead(p); owner=choose_owner(p,s)
    l=Lead(source=p.get("source","api"),name=p["name"].strip(),email=email,company=p.get("company","").strip(),country=p.get("country","").strip(),budget=float(p.get("budget") or 0),interest=p.get("interest","").strip(),score=s,priority=pri,owner=owner,status="new",sla_minutes=15 if pri=="hot" else 60 if pri=="warm" else 240,notes=p.get("notes","").strip())
    db.add(l);db.commit();db.refresh(l);event(db,l.id,"lead_created",f"Scored {s}/100 and routed to {owner}");return l,True
@app.get("/health")
def health():return {"status":"ok"}
@app.get("/")
def dash(request:Request,db:Session=Depends(get_db)):
    leads=list(db.scalars(select(Lead).order_by(Lead.created_at.desc())).all()); now=datetime.utcnow(); events=list(db.scalars(select(Event).order_by(Event.created_at.desc()).limit(8)).all())
    st={"total":len(leads),"hot":sum(x.priority=="hot" for x in leads),"warm":sum(x.priority=="warm" for x in leads),"won":sum(x.status=="won" for x in leads),"avg":round(sum(x.score for x in leads)/len(leads),1) if leads else 0,"overdue":sum(x.status in {"new","contacted"} and now>x.created_at+timedelta(minutes=x.sla_minutes) for x in leads)}
    return templates.TemplateResponse("dashboard.html",{"request":request,"leads":leads[:12],"events":events,"stats":st})
@app.post("/leads")
def create(payload:LeadIn,db:Session=Depends(get_db)):
    l,c=upsert(db,payload.model_dump());return {"created":c,"lead":LeadOut.model_validate(l)}
@app.post("/leads/form")
def form(name:str=Form(...),email:str=Form(...),company:str=Form(""),country:str=Form(""),budget:float=Form(0),interest:str=Form(""),db:Session=Depends(get_db)):
    upsert(db,{"source":"website","name":name,"email":email,"company":company,"country":country,"budget":budget,"interest":interest});return RedirectResponse("/",303)
@app.post("/leads/{lead_id}/status/{status}")
def status(lead_id:int,status:str,db:Session=Depends(get_db)):
    l=db.get(Lead,lead_id)
    if l:l.status=status;db.commit();event(db,l.id,"status_changed",f"Status changed to {status}")
    return RedirectResponse("/",303)
@app.get("/api/leads",response_model=list[LeadOut])
def api_leads(db:Session=Depends(get_db)):return list(db.scalars(select(Lead).order_by(Lead.created_at.desc())).all())
