# LeadSignal HQ

[English](README.md) | **Русский**

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
