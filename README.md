# 🏎️ F1 Race Intelligence

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL 15+](https://img.shields.io/badge/postgresql-15+-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/sqlalchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/alembic-migrations-orange.svg)](https://alembic.sqlalchemy.org/)
[![Tests Passing](https://img.shields.io/badge/tests-134%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An AI-powered Formula 1 race analytics and intelligence platform that transforms raw historical and modern Grand Prix telemetry into structured relational data, deterministic statistical analytics, anomaly detections, and evidence-backed AI explanations.

> **Core Philosophy**: The database and statistical engine are the single source of truth — **never the LLM**. All numbers, rankings, pace metrics, and anomalies are computed deterministically. AI models consume structured evidence packages to synthesize natural-language strategic debriefs and explanations without hallucinating facts.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#environment-setup)
  - [Installation](#installation)
  - [Database Setup & Migrations](#database-setup--migrations)
  - [Running the Ingestion & Smoke Tests](#running-the-ingestion--smoke-tests)
- [Running Tests](#running-tests)
- [Documentation Index](#documentation-index)
- [Development Guidelines](#development-guidelines)

---

## Overview

Formula 1 produces millions of data points across practice, qualifying, sprints, and Grands Prix — from tire compound degradation to telemetry speed traces, sector deltas, pit lane loss times, and strategic undercut windows.

**F1 Race Intelligence** bridges the gap between raw timing streams and actionable racing insights. By combining normalized relational persistence, robust statistical modeling (SciPy, Pandas, SQL CTEs/window functions), and epistemic AI narrative generation, the platform provides deep, trustworthy analysis for engineers, analysts, and passionate fans.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Data_Sources["Data Sources"]
        DS1["Jolpica F1 API\n(Ergast-compatible REST)"]
        DS2["FastF1\n(Telemetry, Weather, Stints)"]
    end

    subgraph Ingestion_ETL["Ingestion & ETL Pipeline"]
        ING["Async API Client\n(httpx, token-bucket rate limiter, cache)"]
        PARSE["Domain Parsers & Time Converters\n(strict ISO 8601, mm:ss.fff, delta, speeds)"]
        ETL["ETL Service & Repositories\n(dependency-ordered, idempotent upserts)"]
    end

    subgraph Storage["Storage Layer (PostgreSQL)"]
        DB[("PostgreSQL 15+\n12 Core Normalized Relational Tables\n+ etl_log Audit Trail")]
        MV[("Materialized Views &\nPrecomputed Indexes")]
    end

    subgraph Analytics["Deterministic Analytics Core"]
        SQL_ENG["SQL Window Functions & CTEs\n(lap deltas, rank progression, pit loss)"]
        PY_ENG["Python Statistical Engine\n(tyre degradation slopes, clean-air pace,\nKDE pit stop distributions, IQR outliers)"]
        EP["Evidence Package Generator\n(structured JSON facts & statistical findings)"]
    end

    subgraph AI_Layer["Grounded AI Explanation Layer"]
        LLM["Provider-Agnostic LLM Interface\n(OpenAI / Anthropic / Gemini)\nStrict Grounding: Explain Evidence, Never Invent"]
    end

    subgraph Serving["API & Presentation"]
        API["FastAPI REST Server\n(Pydantic schemas, typed responses)"]
        UI["React Dashboard\n(TypeScript, Vite, Tailwind CSS, Recharts)"]
    end

    DS1 --> ING
    DS2 --> ING
    ING --> PARSE
    PARSE --> ETL
    ETL --> DB
    DB --> MV
    DB --> SQL_ENG
    MV --> SQL_ENG
    SQL_ENG --> PY_ENG
    PY_ENG --> EP
    EP --> LLM
    SQL_ENG --> API
    LLM --> API
    API --> UI
```

---

## Key Features

### 1. Resilient Data Ingestion & ETL
- **Asynchronous HTTP Client**: Built on `httpx.AsyncClient` with connection pooling, exponential backoff retries, and rate limiting (token bucket / fixed window).
- **Pagination & High Volume**: Transparently handles paginated endpoints (over 900+ lap times, 80+ pit stops per race).
- **Precision Time Parsing**: Robust parsing for all F1 timing representations (`"1:23.456"`, `"+1.234"`, `"PT24.123S"`, millisecond integers, and average speed floats).
- **Idempotent Upserts**: Dependency-aware repository layer utilizing PostgreSQL `ON CONFLICT DO UPDATE` to guarantee safe, repeatable ingestion runs.
- **Audit Logging**: Comprehensive ETL audit trail tracking batch runs, duration, records inserted/updated, and error states in `etl_log`.

### 2. Normalized Relational Database (12 Core Entities)
- Clean, 3NF schema designed specifically for Grand Prix analytics:
  - Reference: `seasons`, `circuits`, `constructors`, `drivers`
  - Event Schedule: `races`
  - Session Outcomes: `race_results`, `qualifying_results`, `sprint_results`
  - Granular Session Telemetry: `pit_stops`, `lap_times`
  - Championship Context: `driver_standings`, `constructor_standings`
- High-performance composite B-Tree indexes for race, driver, lap, and season queries.
- Alembic-managed versioned migrations.

### 3. Deterministic Analytics Engine
- **True Pace Normalization**: Excludes in-laps, out-laps, safety car periods (SC/VSC), and yellow flags.
- **Tyre Degradation Modeling**: Linear and polynomial regression fits tracking lap time loss per compound as stint laps accumulate.
- **Clean-Air Teammate Comparisons**: Isolates driver pace in identical machinery without dirty-air contamination.
- **Pit Lane Performance**: Stationary pit stop duration analysis using Kernel Density Estimation (KDE) and Interquartile Range (IQR).

### 4. Grounded AI Explanations
- **Evidence Packages**: Explanations receive strictly typed JSON evidence bundles containing observed facts and statistical outputs.
- **Epistemic Classification**: Clearly demarcates observed facts, statistical findings, model predictions, and strategic interpretations.
- **Zero Hallucination**: AI generates explanations and narratives — it never computes, extrapolates, or hallucinates telemetry numbers.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Language** | Python 3.10+ |
| **Database** | PostgreSQL 15+ / 16 (Alpine in Docker) |
| **ORM & Migrations** | SQLAlchemy 2.0 (mapped declarative models), Alembic |
| **HTTP & Networking** | httpx (async HTTP/2-ready client) |
| **Data Science & Math** | Pandas, NumPy, SciPy |
| **API Server** | FastAPI, Pydantic v2, Uvicorn |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| **Testing** | pytest, pytest-asyncio, factory/fixtures |
| **Containerization** | Docker, Docker Compose |

---

## Project Structure

```
F1/
├── app/
│   ├── db/                     # Database engine, session, and models
│   │   ├── base.py             # SQLAlchemy declarative Base
│   │   ├── session.py          # Database session factory & connection pool
│   │   └── models/             # SQLAlchemy 2.0 mapped model classes
│   ├── etl/                    # ETL persistence orchestration
│   │   ├── exceptions.py       # Domain-specific ETL exceptions
│   │   ├── repositories/       # Idempotent database repositories
│   │   ├── service.py          # High-level ETL service orchestrator
│   │   └── types.py            # Typed ingestion results & statistics
│   └── f1/                     # Jolpica / Ergast API client & parsing
│       ├── client.py           # Async Jolpica API client with rate limiting
│       ├── exceptions.py       # API and HTTP parsing errors
│       ├── parsing/            # Pydantic schemas, domain parsers, time utilities
│       └── types.py            # Session and query parameter types
├── alembic/                    # Database migration scripts & environment
│   ├── env.py
│   └── versions/               # Versioned migration files
├── docs/                       # Comprehensive specifications & architectural blueprints
│   ├── ai-insight-spec.md      # Grounded LLM prompt & evidence package specs
│   ├── analytics-spec.md       # Statistical & telemetry metric definitions
│   ├── api-client.md           # External API client specification
│   ├── architecture.md         # Deep-dive system architecture
│   ├── data-dictionary.md      # Field-level dictionary & validation limits
│   ├── data-sources.md         # Jolpica & FastF1 endpoint documentation
│   ├── database-schema.md      # Relational schema DDL & relationship maps
│   ├── product-spec.md         # Full product vision and user flows
│   ├── roadmap.md              # Phased implementation roadmap
│   └── decisions/              # Architecture Decision Records (ADRs)
├── scripts/                    # Operational & smoke-test scripts
│   ├── check_db.py             # Database connectivity & table check
│   └── smoke_test_jolpica.py   # Live API integration smoke test
├── tests/                      # Automated test suite (unit & integration)
│   ├── conftest.py             # Reusable database, engine, and API fixtures
│   ├── db/                     # Schema, constraint, and migration tests
│   ├── etl/                    # Repository and ETL service tests
│   └── f1/                     # Client, parser, and time utility tests
├── AGENTS.md                   # AI agent coding instructions & non-negotiables
├── docker-compose.yml          # PostgreSQL service container definition
├── pyproject.toml              # Project dependencies, packaging, and tool config
└── README.md                   # Project description & guide
```

---

## Database Schema

The core relational schema consists of 12 primary analytical tables plus the ETL audit log:

```
seasons ──────────┬──< races ───────┬──< race_results
circuits ─────────┘                 ├──< qualifying_results
                                    ├──< sprint_results
constructors ─────┬──< (results)    ├──< pit_stops
drivers ──────────┘                 ├──< lap_times
                                    ├──< driver_standings
                                    └──< constructor_standings

etl_log (audit trail for ingestion status, durations, and counts)
```

---

## Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **PostgreSQL**: 15 or higher (or Docker)
- **Git**

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yashMsingh/F1.git
   cd F1
   ```

2. Copy the sample environment file:
   ```bash
   cp .env.example .env
   ```

3. Update `.env` with your database credentials (default settings match the `docker-compose.yml` service):
   ```ini
   POSTGRES_DB=f1_race_intelligence
   POSTGRES_USER=f1user
   POSTGRES_PASSWORD=changeme
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   DATABASE_URL=postgresql://f1user:changeme@localhost:5432/f1_race_intelligence
   ```

### Installation

Create and activate a virtual environment, then install the package with development dependencies:

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Install project and dev dependencies
pip install -e ".[dev]"
```

### Database Setup & Migrations

If using Docker, start the PostgreSQL container:

```bash
docker-compose up -d
```

Run Alembic to apply all database migrations:

```bash
alembic upgrade head
```

Verify your database connectivity and tables:

```bash
python scripts/check_db.py
```

### Running the Ingestion & Smoke Tests

Test live Jolpica API access and validation:

```bash
python scripts/smoke_test_jolpica.py
```

---

## Running Tests

The test suite includes comprehensive unit and integration tests covering API clients, parsing pipelines, database schemas, constraints, migrations, and idempotent repositories.

```bash
# Run the complete test suite
pytest tests/

# Run with verbose output and coverage
pytest -v tests/

# Run specific test modules
pytest tests/f1/
pytest tests/db/
pytest tests/etl/
```

---

## Documentation Index

Detailed architectural blueprints, design decisions, and data contracts are maintained under `docs/`:

| Document | Purpose |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Complete system architecture, component boundaries, and pipeline flow |
| [`docs/product-spec.md`](docs/product-spec.md) | Product vision, target personas, user stories, and feature matrix |
| [`docs/database-schema.md`](docs/database-schema.md) | Complete PostgreSQL schema definitions, data types, indexes, and constraints |
| [`docs/analytics-spec.md`](docs/analytics-spec.md) | Mathematical formulas and edge-case handling for all analytics metrics |
| [`docs/data-sources.md`](docs/data-sources.md) | Endpoint catalog and schemas for Jolpica F1 API and FastF1 |
| [`docs/ai-insight-spec.md`](docs/ai-insight-spec.md) | Specification for grounded Evidence Packages and LLM prompt design |
| [`docs/data-dictionary.md`](docs/data-dictionary.md) | Complete attribute catalog, validation bounds, and normalization rules |
| [`docs/roadmap.md`](docs/roadmap.md) | Phase-by-phase implementation status and milestones |
| [`AGENTS.md`](AGENTS.md) | Ground rules, architecture invariants, and coding conventions for AI agents |

---

## Development Guidelines

- **Database Invariance**: The database is the source of truth. Schema mutations must always be performed via Alembic migrations.
- **Idempotency**: Ingestion routines must use `ON CONFLICT` upsert semantics to ensure safe re-runs.
- **Edge Cases**: Always explicitly handle DNFs, DNSs, DSQs, unclassified laps, and wet weather conditions.
- **Type Safety**: Use Python 3.10+ type hints and Pydantic models for data interchange.
- **Testing**: Every new repository, parser, or analytical metric must include automated tests in `tests/`.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details. Data provided by Jolpica (Ergast API successor) and Formula 1 is subject to their respective usage terms.
