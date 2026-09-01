# AGENTS.md — F1 Race Intelligence

> Instructions for AI coding agents working on this project.

## Project Purpose

An AI-powered Formula 1 analytics platform that transforms race data into structured analytics, statistical insights, and evidence-backed AI explanations. The database is the source of truth — never the LLM.

## Architecture

```
Jolpica API / FastF1 → ETL → PostgreSQL → SQL Analytics → Statistics → Insight Detection → Evidence Package → LLM Explanation → Dashboard
```

- **Backend**: Python (FastAPI, SQLAlchemy, Pandas, SciPy)
- **Database**: PostgreSQL (normalized, 12 core tables + ETL log)
- **Frontend**: React + TypeScript + Vite
- **AI**: Provider-agnostic LLM integration (explanation only, not data generation)

## Key Directories

```
docs/               # Architecture, specs, data dictionary, decisions
src/
  ingestion/        # API clients, ETL pipeline
  models/           # SQLAlchemy models
  analytics/        # SQL and Python analytics
  insights/         # Insight detection + AI explanation
  api/              # FastAPI endpoints
frontend/           # React dashboard
tests/              # pytest test suite
migrations/         # Alembic migrations
```

## Coding Conventions

- Python 3.10+, type hints required
- SQLAlchemy 2.0 style (mapped classes)
- Use `httpx` for HTTP requests (async preferred)
- Environment variables for all configuration (never hardcode secrets)
- Logging via Python `logging` module (structured where possible)
- Pydantic models for API request/response schemas
- Tests with `pytest`; analytics tests should verify against known F1 data

## Testing Commands

```bash
pytest tests/                    # Run all tests
pytest tests/unit/               # Unit tests only
pytest tests/integration/        # Integration tests (requires DB)
alembic upgrade head             # Apply all migrations
alembic downgrade -1             # Rollback last migration
```

## Critical Rules

### AI Grounding (NON-NEGOTIABLE)

1. **The LLM is NOT the source of truth.** All numbers come from SQL/Python/statistics.
2. **AI explanations must be grounded in evidence packages.** The LLM receives structured data and explains it — it never generates data.
3. **Distinguish epistemically**: observed fact, statistical finding, model prediction, interpretation. Never present speculation as fact.
4. **No fabricated statistics.** If the data doesn't support a claim, say so.

### Database Rules

1. Schema changes require Alembic migrations — never raw DDL in production.
2. All inserts/updates must be idempotent (use UNIQUE constraints + ON CONFLICT).
3. Never delete source data. If data needs correction, add `updated_at` timestamp.
4. Future "Ask the Data" queries must use a **read-only** database user.
5. Block mutating SQL: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE.

### Analytics Rules

1. Every metric must be defined in `docs/analytics-spec.md` before implementation.
2. Edge cases (DNF, DNS, DSQ, missing grid) must be explicitly handled.
3. Document the denominator for any rate/average (what's included/excluded).
4. Statistical methods must state assumptions and minimum sample sizes.

### Data Quality

1. Never silently discard records. Log and document any skipped data.
2. Parse all string numbers from the API in ETL (they come as strings).
3. Store both original string and parsed numeric for time values.
4. Handle pagination for laps (900+) and pit stops (80+) endpoints.

## Documentation

- Read `docs/` before making architectural changes.
- New architectural decisions go in `docs/decisions/` with: Context, Decision, Alternatives, Reason, Consequences.
- Update `docs/analytics-spec.md` when adding new metrics.

## Git Workflow

- `main` branch for stable code
- Feature branches: `feature/data-ingestion`, `feature/sql-analytics`, etc.
- Small, focused commits with descriptive messages
- No large unrelated changes in a single commit
