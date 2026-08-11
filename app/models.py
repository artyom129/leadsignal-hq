from datetime import datetime
from sqlalchemy import String,Integer,DateTime,Float,Text
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class Lead(Base):
    __tablename__="leads"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    source:Mapped[str]=mapped_column(String(50),default="website")
    name:Mapped[str]=mapped_column(String(120))
    email:Mapped[str]=mapped_column(String(180),index=True)
    company:Mapped[str]=mapped_column(String(180),default="")
    country:Mapped[str]=mapped_column(String(80),default="")
    budget:Mapped[float]=mapped_column(Float,default=0)
    interest:Mapped[str]=mapped_column(String(120),default="")
    score:Mapped[int]=mapped_column(Integer,default=0)
    priority:Mapped[str]=mapped_column(String(20),default="normal")
    owner:Mapped[str]=mapped_column(String(80),default="Unassigned")
    status:Mapped[str]=mapped_column(String(30),default="new")
    sla_minutes:Mapped[int]=mapped_column(Integer,default=60)
    notes:Mapped[str]=mapped_column(Text,default="")
class Event(Base):
    __tablename__="events"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    lead_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
    event_type:Mapped[str]=mapped_column(String(50))
    detail:Mapped[str]=mapped_column(Text,default="")
