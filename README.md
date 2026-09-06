<a id="english"></a>

<div align="center">

**🇬🇧 English** · [🇷🇺 Русский](#russian)

</div>

# LeadSignal HQ

**Lead qualification, routing, SLA tracking, and CRM-ready automation.**

LeadSignal HQ is a production-style FastAPI application for businesses that collect leads from multiple channels and need to respond quickly without manually sorting every contact.

## What it does

```text
Website / Ads / API
        ↓
Deduplicate
        ↓
Validate + normalize
        ↓
Business scoring
        ↓
Priority + owner routing
        ↓
SLA tracking
        ↓
CRM / alerts / follow-up
```

### Features
- REST API + web-form lead intake
- Duplicate blocking by email
- Rule-based lead scoring
- Hot / warm / normal priority
- Automatic routing to Backend, Automation, Sales, or Senior Sales queues
- SLA timers for response urgency
- Lead status workflow
- SQLite audit trail
- Dark operations dashboard with KPIs
- Swagger/OpenAPI docs
- Docker
- Pytest tests
- Seeded demo data

### Stack
Python · FastAPI · SQLAlchemy · SQLite · Jinja2 · REST API · Docker · Pytest

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seed_demo.py
uvicorn app.main:app --reload
```

Dashboard: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

## Portfolio positioning
This is a personal demonstration project built to showcase business automation, API development, data validation, routing logic, and operational dashboards. It does not claim to be client work.

---

<a id="russian"></a>

<div align="center">

[🇬🇧 English](#english) · **🇷🇺 Русский**

</div>

# LeadSignal HQ — Русская версия

**Автоматическая квалификация лидов, маршрутизация, SLA-контроль и подготовка данных для CRM.**

LeadSignal HQ — production-style FastAPI-приложение для компаний, которые получают заявки из нескольких источников и хотят быстро распределять их без ручной сортировки.

## Как работает

```text
Сайт / реклама / API
        ↓
     Дедупликация
        ↓
Проверка + нормализация
        ↓
   Business scoring
        ↓
Приоритет + назначение
        ↓
      SLA tracking
        ↓
CRM / alerts / follow-up
```

## Возможности

- приём лидов через REST API и web form;
- блокировка дублей по email;
- rule-based scoring;
- приоритеты hot / warm / normal;
- автоматическое распределение в Backend, Automation, Sales или Senior Sales;
- SLA-таймеры;
- workflow статусов лида;
- audit trail в SQLite;
- operations dashboard с KPI;
- Swagger/OpenAPI;
- Docker;
- Pytest;
- demo-данные.

## Стек

Python · FastAPI · SQLAlchemy · SQLite · Jinja2 · REST API · Docker · Pytest

## Запуск

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seed_demo.py
uvicorn app.main:app --reload
```

Dashboard: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

Проект демонстрирует business automation, API-разработку, валидацию данных, scoring/routing logic и операционные панели. Это личный демонстрационный проект, а не заявленная клиентская работа.
