# natiah

Natiah is a small outreach automation stack that combines:

- A FastAPI backend (REST API, PostgreSQL, Redis, Alembic migrations)
- A Next.js frontend (dashboard/UI)
- Celery workers (campaign scheduling + background jobs)
- A Playwright-based automation runner (executes LinkedIn actions)

## Repository Layout

- backend/ — FastAPI app, DB models, migrations, API endpoints
- frontend/ — Next.js UI
- workers/ — Celery task implementations + Celery app config
- automation/ — Playwright automation engine + job runner
- docker/ — Dockerfiles and docker-compose configs

## How Outreach Works (High Level)

1. You connect a LinkedIn account (OAuth or session/cookie-based flow).
2. You add leads (prospects) under a LinkedIn account.
3. You create a campaign and define message sequence steps.
4. You start the campaign.
5. Workers schedule “sequence actions” for leads (connect, message, etc.).
6. The scheduler dispatches due actions, which enqueue automation jobs.
7. The automation runner executes those jobs using Playwright.

The campaign “start” endpoint triggers scheduling:
- POST /api/v1/campaigns/{campaign_id}/start

## Quick Start (Docker Compose)

Prerequisites:
- Docker + Docker Compose

1) Create environment files (do not commit real secrets)

- docker/.env.example is provided as a template.
- Create docker/.env locally and fill in values as needed.

2) Start the stack

```bash
cd docker
docker compose up --build
```

Services in docker-compose.yml:
- postgres (database)
- redis (broker/backend for Celery)
- backend (FastAPI on :8000)
- frontend (Next.js on :3000)
- worker (Celery worker)
- beat (Celery beat scheduler, dispatches due actions every 60s)
- automation_runner (executes automation jobs with Playwright)

3) Open the app

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1

## Local Development (Without Docker)

You can also run services directly, but you still need Postgres + Redis.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- -p 3000
```

Worker + Beat:

```bash
celery -A workers.celery_app.celery_app worker -l INFO
celery -A workers.celery_app.celery_app beat -l INFO
```

Automation runner:

```bash
python -m automation.runner
```

## Environment Variables

The backend and workers use these (see docker/docker-compose.yml):

- DATABASE_URL
- REDIS_URL
- JWT_SECRET
- CORS_ORIGINS
- DB_AUTO_CREATE
- LINKEDIN_CLIENT_ID
- LINKEDIN_CLIENT_SECRET
- LINKEDIN_CALLBACK_URL
- LINKEDIN_SCOPES

Important:
- Do not commit any real secrets (GitHub push protection will block them).
- Use *.env.example files for templates.

## Key API Endpoints

Authentication:
- POST /api/v1/auth/register
- POST /api/v1/auth/login

Accounts:
- GET /api/v1/accounts
- POST /api/v1/accounts
- POST /api/v1/accounts/{account_id}/oauth/init
- GET /api/v1/accounts/oauth/callback

Leads:
- GET /api/v1/leads?account_id=...
- POST /api/v1/leads
- POST /api/v1/leads/scrape/sales-navigator

Campaigns:
- GET /api/v1/campaigns
- POST /api/v1/campaigns
- POST /api/v1/campaigns/{campaign_id}/start
- POST /api/v1/campaigns/{campaign_id}/stop

Sequences:
- GET /api/v1/sequences?campaign_id=...
- POST /api/v1/sequences

## Notes on Safety

This project can automate LinkedIn actions. Use conservative limits and respect platform policies.

Also note that automation/profiles/ may contain local browser session state. It is intentionally ignored from git.

## Deployment

See docker/DEPLOYMENT_UBUNTU.md for a deployment guide.
