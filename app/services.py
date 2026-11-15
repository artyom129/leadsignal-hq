import csv
import io
import math
import re
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Event, Lead, utcnow
from .scoring import SLA_MINUTES, choose_owner, score_lead

STATUSES = ("new", "contacted", "qualified", "won", "lost")
PRIORITIES = ("hot", "warm", "normal")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class LeadError(ValueError):
    """Bad input; the message is safe to show to the user."""


def clean_payload(p: dict) -> dict:
    """Validate and normalize raw lead data."""
    name = " ".join(str(p.get("name") or "").split())
    email = str(p.get("email") or "").strip().lower()
    if not name:
        raise LeadError("Name is required")
    if len(name) > 120:
        raise LeadError("Name is longer than 120 characters")
    if len(email) > 180 or not EMAIL_RE.match(email):
        raise LeadError("Email address is not valid")
    try:
        budget = float(p.get("budget") or 0)
    except (TypeError, ValueError):
        raise LeadError("Budget must be a number") from None
    if not math.isfinite(budget) or budget < 0:
        raise LeadError("Budget must be zero or more")
    return {
        "source": str(p.get("source") or "api").strip()[:50] or "api",
        "name": name,
        "email": email,
        "company": str(p.get("company") or "").strip()[:180],
        "country": str(p.get("country") or "").strip()[:80],
        "budget": budget,
        "interest": str(p.get("interest") or "").strip()[:120],
        "notes": str(p.get("notes") or "").strip(),
    }


def log(db: Session, lead_id: int | None, kind: str, detail: str) -> None:
    db.add(Event(lead_id=lead_id, event_type=kind, detail=detail))


def create_lead(db: Session, raw: dict) -> tuple[Lead, bool]:
    """Return (lead, created). A duplicate email returns the existing lead."""
    p = clean_payload(raw)
    existing = db.scalar(select(Lead).where(Lead.email == p["email"]))
    if existing is None:
        score, priority = score_lead(p)
        owner = choose_owner(p, score)
        lead = Lead(**p, score=score, priority=priority, owner=owner, status="new",
                    sla_minutes=SLA_MINUTES[priority])
        db.add(lead)
        try:
            db.flush()
        except IntegrityError:  # two requests with the same email at once
            db.rollback()
            existing = db.scalar(select(Lead).where(Lead.email == p["email"]))
        else:
            log(db, lead.id, "lead_created", f"Scored {score}/100 ({priority}) and routed to {owner}")
            db.commit()
            db.refresh(lead)
            return lead, True
    log(db, existing.id, "duplicate_blocked", f"Duplicate ignored from {p['source']}")
    db.commit()
    return existing, False


def set_status(db: Session, lead_id: int, status: str) -> Lead | None:
    if status not in STATUSES:
        raise LeadError(f"Status must be one of: {', '.join(STATUSES)}")
    lead = db.get(Lead, lead_id)
    if lead is None:
        return None
    if lead.status != status:
        old, lead.status = lead.status, status
        log(db, lead.id, "status_changed", f"{old} -> {status}")
        db.commit()
    return lead


def due_at(lead: Lead):
    return lead.created_at + timedelta(minutes=lead.sla_minutes)


def is_overdue(lead: Lead, now=None) -> bool:
    """The SLA is the time to first response, so only untouched leads can be overdue."""
    return lead.status == "new" and (now or utcnow()) > due_at(lead)


def minutes_left(lead: Lead, now=None) -> int:
    return int((due_at(lead) - (now or utcnow())).total_seconds() // 60)


def search(db: Session, q: str = "", status: str = "", priority: str = "",
           limit: int = 100, offset: int = 0) -> tuple[list[Lead], int]:
    stmt = select(Lead)
    if q.strip():
        # % and _ typed into the search box are literal characters, not wildcards.
        term = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{term}%"
        stmt = stmt.where(or_(*(func.lower(column).like(like, escape="\\")
                                for column in (Lead.name, Lead.email, Lead.company, Lead.interest))))
    if status in STATUSES:
        stmt = stmt.where(Lead.status == status)
    if priority in PRIORITIES:
        stmt = stmt.where(Lead.priority == priority)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Lead.created_at.desc(), Lead.id.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def stats(db: Session) -> dict:
    leads = list(db.scalars(select(Lead)).all())
    now = utcnow()
    closed = sum(x.status in {"won", "lost"} for x in leads)
    won = sum(x.status == "won" for x in leads)
    return {
        "total": len(leads),
        "hot": sum(x.priority == "hot" for x in leads),
        "warm": sum(x.priority == "warm" for x in leads),
        "won": won,
        "win_rate": round(100 * won / closed, 1) if closed else 0,
        "avg_score": round(sum(x.score for x in leads) / len(leads), 1) if leads else 0,
        "overdue": sum(is_overdue(x, now) for x in leads),
        "pipeline_value": round(sum(x.budget for x in leads if x.status not in {"won", "lost"}), 2),
        "by_status": {s: sum(x.status == s for x in leads) for s in STATUSES},
    }


EVENT_TEXT = {
    "lead_created": "came in",
    "duplicate_blocked": "sent again, duplicate ignored",
    "status_changed": "moved",
}


def recent_activity(db: Session, limit: int = 10) -> list[dict]:
    """Latest events as readable lines, with the lead's name."""
    rows = db.execute(
        select(Event, Lead.name).outerjoin(Lead, Lead.id == Event.lead_id)
        .order_by(Event.created_at.desc(), Event.id.desc()).limit(limit)
    ).all()
    return [{"event": event, "name": name or "Removed lead", "verb": EVENT_TEXT.get(event.event_type, event.event_type)}
            for event, name in rows]


def response_board(leads: list[Lead], now=None, window_minutes: int = 240) -> dict:
    """Unanswered leads placed on a line from 'already late' to 'due in 4 hours'.

    0-20% is the overdue zone, 20% is now, 100% is the end of the window. The
    scale is a square root, so the next 15 minutes, where the urgent leads
    sit, get as much room as the two hours after them.
    """
    now = now or utcnow()
    items = []
    for lead in leads:
        if lead.status != "new":
            continue
        left = minutes_left(lead, now)
        if left > window_minutes:
            continue
        items.append({"lead": lead, "left": left, "position": board_position(left, window_minutes), "late": left < 0})
    items.sort(key=lambda item: item["left"])
    ticks = [{"label": label, "position": board_position(minutes, window_minutes)}
             for label, minutes in (("-1 h", -60), ("+15 min", 15), ("+1 h", 60), ("+2 h", 120), ("+4 h", 240))]
    return {"items": items, "window": window_minutes, "ticks": ticks}


LATE_SPAN = 60  # how far back the overdue zone reaches, in minutes


def board_position(left: int, window_minutes: int = 240) -> float:
    if left < 0:
        return round(20 * (1 - math.sqrt(min(-left, LATE_SPAN) / LATE_SPAN)), 2)
    return round(20 + 80 * math.sqrt(min(left, window_minutes) / window_minutes), 2)


def _safe_cell(v):
    # Spreadsheet programs run text that starts with = + - @ as a formula.
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def to_csv(leads: list[Lead]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "created_at", "source", "name", "email", "company", "country", "budget",
                "interest", "score", "priority", "owner", "status", "due_at"])
    for l in leads:
        w.writerow([_safe_cell(v) for v in (
            l.id, l.created_at.isoformat(timespec="seconds"), l.source, l.name, l.email, l.company,
            l.country, l.budget, l.interest, l.score, l.priority, l.owner, l.status,
            due_at(l).isoformat(timespec="seconds"))])
    return out.getvalue()
