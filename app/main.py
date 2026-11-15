from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import services
from .db import SessionLocal, init_db
from .models import Event, Lead, utcnow
from .scoring import breakdown

BASE = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LeadSignal HQ", version="1.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE / "app" / "static")), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LeadIn(BaseModel):
    source: str = "api"
    name: str
    email: str
    company: str = ""
    country: str = ""
    budget: float = 0
    interest: str = ""
    notes: str = ""


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    source: str
    name: str
    email: str
    company: str
    country: str
    budget: float
    interest: str
    notes: str
    score: int
    priority: str
    owner: str
    status: str
    sla_minutes: int


class StatusIn(BaseModel):
    status: str


@app.exception_handler(services.LeadError)
async def lead_error(request: Request, exc: services.LeadError):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    # People in the browser get a page; the API keeps JSON errors.
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/docs", "/openapi")):
        return templates.TemplateResponse(request, "not_found.html", {}, status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "degraded", "database": "unavailable"}, status_code=503)
    return {"status": "ok", "database": "ok"}


@app.get("/")
def dashboard(request: Request, q: str = "", status: str = "", priority: str = "",
              msg: str = "", db: Session = Depends(get_db)):
    leads, total = services.search(db, q, status, priority, limit=50)
    unanswered, _ = services.search(db, status="new", limit=500)
    now = utcnow()
    rows = [{"lead": l, "overdue": services.is_overdue(l, now),
             "left": services.minutes_left(l, now)} for l in leads]
    return templates.TemplateResponse(request, "dashboard.html", {
        "rows": rows, "activity": services.recent_activity(db, 9), "stats": services.stats(db),
        "board": services.response_board(unanswered, now), "matched": total,
        "q": q, "status": status, "priority": priority, "msg": msg,
        "statuses": services.STATUSES, "priorities": services.PRIORITIES,
    })


@app.get("/leads/{lead_id}")
def lead_page(request: Request, lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    events = db.scalars(select(Event).where(Event.lead_id == lead.id)
                        .order_by(Event.created_at.desc(), Event.id.desc())).all()
    parts = breakdown({"budget": lead.budget, "company": lead.company,
                       "interest": lead.interest, "country": lead.country})
    now = utcnow()
    return templates.TemplateResponse(request, "lead.html", {
        "lead": lead, "events": events, "parts": parts, "statuses": services.STATUSES,
        "overdue": services.is_overdue(lead, now), "left": services.minutes_left(lead, now),
        "due": services.due_at(lead),
    })


@app.post("/leads")
def create(payload: LeadIn, db: Session = Depends(get_db)):
    lead, created = services.create_lead(db, payload.model_dump())
    return {"created": created, "lead": LeadOut.model_validate(lead)}


@app.post("/leads/form")
def form(name: str = Form(""), email: str = Form(""), company: str = Form(""), country: str = Form(""),
         budget: str = Form("0"), interest: str = Form(""), db: Session = Depends(get_db)):
    try:
        lead, created = services.create_lead(db, {
            "source": "website", "name": name, "email": email, "company": company,
            "country": country, "budget": budget, "interest": interest})
        msg = (f"Lead created: {lead.name}, score {lead.score}, owner {lead.owner}" if created
               else f"{lead.email} already exists, duplicate ignored")
    except services.LeadError as e:
        msg = f"Not saved: {e}"
    return RedirectResponse(f"/?msg={quote(msg)}", 303)


@app.post("/leads/{lead_id}/status/{status}")
def change_status_form(lead_id: int, status: str, db: Session = Depends(get_db)):
    try:
        lead = services.set_status(db, lead_id, status)
    except services.LeadError as e:
        raise HTTPException(422, str(e)) from None
    if lead is None:
        raise HTTPException(404, "Lead not found")
    return RedirectResponse(f"/leads/{lead_id}", 303)


@app.get("/api/leads", response_model=list[LeadOut])
def api_leads(q: str = "", status: str = "", priority: str = "",
              limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
              db: Session = Depends(get_db)):
    return services.search(db, q, status, priority, limit, offset)[0]


@app.get("/api/leads/export.csv")
def export_csv(q: str = "", status: str = "", priority: str = "", db: Session = Depends(get_db)):
    leads, _ = services.search(db, q, status, priority, limit=100000)
    return Response(services.to_csv(leads), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="leads.csv"'})


@app.get("/api/leads/{lead_id}", response_model=LeadOut)
def api_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    return lead


@app.patch("/api/leads/{lead_id}/status", response_model=LeadOut)
def api_status(lead_id: int, body: StatusIn, db: Session = Depends(get_db)):
    lead = services.set_status(db, lead_id, body.status)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    return lead


@app.get("/api/stats")
def api_stats(db: Session = Depends(get_db)):
    return services.stats(db)
